"""
Seleção de Arquivos - File Selector
Seleciona e exporta arquivos modificados após uma data/hora específica,
mantendo a estrutura de pastas original.
"""

import json
import os
import re
import sys
import shutil
import threading
import zipfile
from datetime import datetime

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Messagebox
from ttkbootstrap.widgets import DateEntry
from tkinter import filedialog


def _get_config_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "file_selector_config.json")


EXT_MODES = ["Todas", "Ignorar extensões", "Somente essas extensões"]
FOLDER_MODES = ["Todas", "Ignorar pastas", "Somente essas pastas"]

DEFAULT_CONFIG = {
    "source_history": [],
    "dest_history": [],
    "folder_links": {},
    "ext_mode": "Ignorar extensões",
    "ext_ignore_val": ".svn-base,.ini,.bak,.db,.config",
    "ext_only_val": "",
    "folder_mode": "Ignorar pastas",
    "folder_ignore_val": ".git,.svn,node_modules,vendor,bin,obj,__pycache__",
    "folder_only_val": "",
    "theme": "cosmo",
    "max_export_folders": 50,
}


class FileSelector:
    def __init__(self, root):
        self.root = root
        self.root.title("File Selector")
        self.root.geometry("1100x800")
        self.root.minsize(950, 650)

        # Ícone da janela
        icon_path = os.path.join(
            os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__)),
            "file_selector.ico"
        )
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        self.files_data = []
        self.scanning = False
        self.sort_col = None
        self.sort_reverse = False

        self._load_config()
        self._build_ui()

        # Aplicar link de destino se já houver uma origem no histórico
        source = self.var_path.get().strip()
        if source:
            self._apply_folder_link(source)

    # --- Config ---

    def _load_config(self):
        self.cfg = dict(DEFAULT_CONFIG)
        try:
            with open(_get_config_path(), "r", encoding="utf-8") as f:
                saved = json.load(f)
                # Migrar config antigo: folder_history → source_history
                if "folder_history" in saved and "source_history" not in saved:
                    saved["source_history"] = saved.pop("folder_history")
                self.cfg.update(saved)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save_config(self):
        # Salvar o valor atual no slot correto antes de gravar
        ext_mode = self.var_ext_mode.get()
        if ext_mode == "Ignorar extensões":
            self.cfg["ext_ignore_val"] = self.var_ext_value.get()
        elif ext_mode == "Somente essas extensões":
            self.cfg["ext_only_val"] = self.var_ext_value.get()

        folder_mode = self.var_folder_mode.get()
        if folder_mode == "Ignorar pastas":
            self.cfg["folder_ignore_val"] = self.var_folder_value.get()
        elif folder_mode == "Somente essas pastas":
            self.cfg["folder_only_val"] = self.var_folder_value.get()

        self.cfg.update({
            "ext_mode": ext_mode,
            "folder_mode": folder_mode,
            "theme": self.root.style.theme.name,
        })
        try:
            with open(_get_config_path(), "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _add_to_history(self, path, history_type="source"):
        path = os.path.normpath(path)
        key = "source_history" if history_type == "source" else "dest_history"
        history = self.cfg[key]
        if path in history:
            history.remove(path)
        history.insert(0, path)
        self.cfg[key] = history[:20]
        self._save_config()
        if history_type == "source":
            self.combo_path["values"] = self.cfg["source_history"]

    # --- UI ---

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill=BOTH, expand=True)

        # === HEADER ===
        header = ttk.Frame(main)
        header.pack(fill=X, pady=(0, 12))
        ttk.Label(header, text="File Selector", font=("-size", 18, "-weight", "bold"),
                  bootstyle="primary").pack(side=LEFT)
        ttk.Label(header, text="Exportar arquivos modificados",
                  font=("-size", 10), bootstyle="secondary").pack(side=LEFT, padx=(12, 0), pady=(6, 0))

        frame_theme = ttk.Frame(header)
        frame_theme.pack(side=RIGHT)
        ttk.Label(frame_theme, text="Tema:", font=("-size", 9)).pack(side=LEFT, padx=(0, 4))
        themes = sorted(self.root.style.theme_names())
        self.var_theme = ttk.StringVar(value=self.root.style.theme.name)
        combo_theme = ttk.Combobox(frame_theme, textvariable=self.var_theme,
                                    values=themes, state="readonly", width=14, font=("-size", 9))
        combo_theme.pack(side=LEFT)
        combo_theme.bind("<<ComboboxSelected>>", self._change_theme)

        # === PASTA DE ORIGEM ===
        card_path = ttk.Labelframe(main, text="  Pasta de origem  ", padding=10, bootstyle="primary")
        card_path.pack(fill=X, pady=(0, 8))

        self.var_path = ttk.StringVar()
        self.combo_path = ttk.Combobox(card_path, textvariable=self.var_path,
                                        values=self.cfg["source_history"], font=("-size", 10))
        self.combo_path.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        if self.cfg["source_history"]:
            self.combo_path.current(0)
        self.combo_path.bind("<<ComboboxSelected>>", self._on_source_selected)

        ttk.Button(card_path, text="Procurar...", command=self._browse_source,
                   bootstyle="primary-outline").pack(side=RIGHT)

        # === FILTROS ===
        card_filters = ttk.Labelframe(main, text="  Filtros  ", padding=10, bootstyle="info")
        card_filters.pack(fill=X, pady=(0, 8))

        # Linha 1: Extensões
        row_ext = ttk.Frame(card_filters)
        row_ext.pack(fill=X, pady=(0, 6))

        ttk.Label(row_ext, text="Extensões:", font=("-size", 9, "-weight", "bold"), width=10).pack(side=LEFT)
        self.var_ext_mode = ttk.StringVar(value=self.cfg["ext_mode"])
        self.combo_ext_mode = ttk.Combobox(row_ext, textvariable=self.var_ext_mode,
                                            values=EXT_MODES, state="readonly", width=24, font=("-size", 9))
        self.combo_ext_mode.pack(side=LEFT, padx=(0, 8))
        self.combo_ext_mode.bind("<<ComboboxSelected>>", self._on_ext_mode_change)

        self.var_ext_value = ttk.StringVar()
        self.entry_ext = ttk.Entry(row_ext, textvariable=self.var_ext_value, font=("-size", 9))
        self.entry_ext.pack(side=LEFT, fill=X, expand=True)
        self._load_ext_field()

        # Linha 2: Pastas
        row_folder = ttk.Frame(card_filters)
        row_folder.pack(fill=X, pady=(0, 6))

        ttk.Label(row_folder, text="Pastas:", font=("-size", 9, "-weight", "bold"), width=10).pack(side=LEFT)
        self.var_folder_mode = ttk.StringVar(value=self.cfg["folder_mode"])
        self.combo_folder_mode = ttk.Combobox(row_folder, textvariable=self.var_folder_mode,
                                               values=FOLDER_MODES, state="readonly", width=24, font=("-size", 9))
        self.combo_folder_mode.pack(side=LEFT, padx=(0, 8))
        self.combo_folder_mode.bind("<<ComboboxSelected>>", self._on_folder_mode_change)

        self.var_folder_value = ttk.StringVar()
        self.entry_folder = ttk.Entry(row_folder, textvariable=self.var_folder_value, font=("-size", 9))
        self.entry_folder.pack(side=LEFT, fill=X, expand=True)
        self._load_folder_field()

        # Linha 3: Modificados a partir de
        row_date = ttk.Frame(card_filters)
        row_date.pack(fill=X)

        ttk.Label(row_date, text="A partir de:", font=("-size", 9, "-weight", "bold"), width=10).pack(side=LEFT)
        self.date_entry = DateEntry(row_date, dateformat="%d/%m/%Y", width=12, bootstyle="info")
        self.date_entry.pack(side=LEFT, padx=(0, 8))

        self.var_hour = ttk.StringVar(value="00")
        self.var_minute = ttk.StringVar(value="00")
        ttk.Spinbox(row_date, from_=0, to=23, width=3, textvariable=self.var_hour,
                     format="%02.0f", wrap=True, bootstyle="info").pack(side=LEFT)
        ttk.Label(row_date, text=":", font=("-size", 12, "-weight", "bold")).pack(side=LEFT)
        ttk.Spinbox(row_date, from_=0, to=59, width=3, textvariable=self.var_minute,
                     format="%02.0f", wrap=True, bootstyle="info").pack(side=LEFT)

        # === BOTÕES DE AÇÃO ===
        frame_actions = ttk.Frame(main)
        frame_actions.pack(fill=X, pady=(0, 8))

        ttk.Button(frame_actions, text="Listar arquivos", command=self._list_files,
                   bootstyle="success", width=20).pack(side=LEFT, padx=(0, 8))
        ttk.Button(frame_actions, text="Cancelar", command=self._cancel_scan,
                   bootstyle="warning-outline", width=15).pack(side=LEFT, padx=(0, 8))
        ttk.Button(frame_actions, text="Limpar tudo", command=self._clear_all,
                   bootstyle="danger-outline", width=15).pack(side=LEFT)

        # === TABELA DE ARQUIVOS ===
        card_files = ttk.Labelframe(main, text="  Arquivos encontrados  ", padding=8, bootstyle="secondary")
        card_files.pack(fill=BOTH, expand=True, pady=(0, 8))

        toolbar = ttk.Frame(card_files)
        toolbar.pack(fill=X, pady=(0, 6))

        self.var_select_all = ttk.BooleanVar(value=False)
        ttk.Checkbutton(toolbar, text="Selecionar todos", variable=self.var_select_all,
                         command=self._toggle_select_all, bootstyle="primary-round-toggle").pack(side=LEFT)

        self.lbl_count = ttk.Label(toolbar, text="Nenhum arquivo listado", bootstyle="secondary")
        self.lbl_count.pack(side=RIGHT)

        # Treeview com sort
        columns = ("check", "nome", "pasta", "modificado", "tamanho")
        self.tree = ttk.Treeview(card_files, columns=columns, show="headings",
                                  selectmode="extended", bootstyle="primary")

        for col, text, anchor_, width, minw, stretch in [
            ("check", "✓", CENTER, 40, 40, False),
            ("nome", "Nome", W, 200, 120, True),
            ("pasta", "Pasta", W, 350, 180, True),
            ("modificado", "Modificado", W, 160, 120, True),
            ("tamanho", "Tamanho", E, 100, 80, True),
        ]:
            self.tree.column(col, width=width, minwidth=minw, stretch=stretch, anchor=anchor_)
            if col != "check":
                self.tree.heading(col, text=text, anchor=anchor_,
                                  command=lambda c=col: self._sort_by_column(c))
            else:
                self.tree.heading(col, text=text)

        scrollbar_y = ttk.Scrollbar(card_files, orient=VERTICAL, command=self.tree.yview,
                                     bootstyle="primary-round")
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar_y.pack(side=RIGHT, fill=Y)

        self.tree.bind("<Double-1>", self._toggle_check)
        self.tree.bind("<space>", self._toggle_check)

        # === EXPORTAÇÃO ===
        card_export = ttk.Labelframe(main, text="  Exportação  ", padding=10, bootstyle="success")
        card_export.pack(fill=X)

        row_export = ttk.Frame(card_export)
        row_export.pack(fill=X)

        # Opções à esquerda
        frame_opts = ttk.Frame(row_export)
        frame_opts.pack(side=LEFT)

        self.var_gen_structure = ttk.BooleanVar(value=True)
        ttk.Checkbutton(frame_opts, text="Manter estrutura de pastas",
                         variable=self.var_gen_structure, bootstyle="success-round-toggle").pack(anchor=W, pady=(0, 2))
        self.var_gen_txt = ttk.BooleanVar(value=False)
        ttk.Checkbutton(frame_opts, text="Gerar relatório .txt",
                         variable=self.var_gen_txt, bootstyle="success-round-toggle").pack(anchor=W, pady=(0, 2))
        self.var_export_zip = ttk.BooleanVar(value=False)
        ttk.Checkbutton(frame_opts, text="Compactar em .zip",
                         variable=self.var_export_zip, bootstyle="success-round-toggle").pack(anchor=W, pady=(0, 2))

        frame_max_folders = ttk.Frame(frame_opts)
        frame_max_folders.pack(anchor=W)
        ttk.Label(frame_max_folders, text="Máx. pastas no destino:", font=("-size", 8)).pack(side=LEFT)
        self.var_max_export_folders = ttk.IntVar(value=self.cfg.get("max_export_folders", 50))
        ttk.Spinbox(frame_max_folders, textvariable=self.var_max_export_folders,
                     from_=1, to=999, width=5, font=("-size", 8),
                     command=self._on_max_folders_change).pack(side=LEFT, padx=(4, 0))

        # Destino à direita
        frame_dest = ttk.Frame(row_export)
        frame_dest.pack(side=RIGHT)

        ttk.Button(frame_dest, text="Exportar", command=self._export,
                   bootstyle="success", width=14).pack(side=RIGHT, padx=(8, 0))
        ttk.Button(frame_dest, text="Procurar...", command=self._browse_dest,
                   bootstyle="success-outline").pack(side=RIGHT, padx=(8, 0))

        self.var_dest = ttk.StringVar()
        self.combo_dest = ttk.Combobox(frame_dest, textvariable=self.var_dest,
                                        values=self.cfg["dest_history"], font=("-size", 9), width=40)
        self.combo_dest.pack(side=RIGHT)
        if self.cfg["dest_history"]:
            self.combo_dest.current(0)

        ttk.Label(frame_dest, text="Destino:", font=("-size", 9, "-weight", "bold")).pack(side=RIGHT, padx=(0, 6))

        # Barra de progresso + Painel de log
        ttk.Separator(card_export).pack(fill=X, pady=(10, 6))

        self.progress = ttk.Progressbar(card_export, bootstyle="success-striped", mode="determinate")
        self.progress.pack(fill=X, pady=(0, 6))

        self.txt_panel = ttk.Text(card_export, height=3, font=("-size", 9))
        self.txt_panel.configure(state="disabled")
        self.txt_panel.pack(fill=X)

    # --- Helpers ---

    def _log(self, msg):
        self.txt_panel.configure(state="normal")
        self.txt_panel.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.txt_panel.see("end")
        self.txt_panel.configure(state="disabled")

    def _update_counter(self):
        total = len(self.files_data)
        selected = sum(1 for f in self.files_data if f["selected"])
        self.lbl_count.configure(text=f"{selected} de {total} selecionado(s)")

    def _load_ext_field(self):
        mode = self.var_ext_mode.get()
        if mode == "Todas":
            self.var_ext_value.set("")
            self.entry_ext.configure(state="disabled")
        elif mode == "Ignorar extensões":
            self.entry_ext.configure(state="normal")
            self.var_ext_value.set(self.cfg.get("ext_ignore_val", ""))
        elif mode == "Somente essas extensões":
            self.entry_ext.configure(state="normal")
            self.var_ext_value.set(self.cfg.get("ext_only_val", ""))

    def _on_ext_mode_change(self, event=None):
        # Salvar valor atual no slot correto antes de trocar
        old_mode = self.cfg.get("ext_mode", "Todas")
        if old_mode == "Ignorar extensões":
            self.cfg["ext_ignore_val"] = self.var_ext_value.get()
        elif old_mode == "Somente essas extensões":
            self.cfg["ext_only_val"] = self.var_ext_value.get()
        self.cfg["ext_mode"] = self.var_ext_mode.get()
        self._load_ext_field()
        self._save_config()

    def _load_folder_field(self):
        mode = self.var_folder_mode.get()
        if mode == "Todas":
            self.var_folder_value.set("")
            self.entry_folder.configure(state="disabled")
        elif mode == "Ignorar pastas":
            self.entry_folder.configure(state="normal")
            self.var_folder_value.set(self.cfg.get("folder_ignore_val", ""))
        elif mode == "Somente essas pastas":
            self.entry_folder.configure(state="normal")
            self.var_folder_value.set(self.cfg.get("folder_only_val", ""))

    def _on_folder_mode_change(self, event=None):
        old_mode = self.cfg.get("folder_mode", "Todas")
        if old_mode == "Ignorar pastas":
            self.cfg["folder_ignore_val"] = self.var_folder_value.get()
        elif old_mode == "Somente essas pastas":
            self.cfg["folder_only_val"] = self.var_folder_value.get()
        self.cfg["folder_mode"] = self.var_folder_mode.get()
        self._load_folder_field()
        self._save_config()

    def _on_max_folders_change(self):
        self.cfg["max_export_folders"] = self.var_max_export_folders.get()
        self._save_config()

    def _change_theme(self, event=None):
        self.root.style.theme_use(self.var_theme.get())
        self._save_config()

    def _on_source_selected(self, event=None):
        """Quando o usuário seleciona uma origem do histórico, aplica o link."""
        source = self.var_path.get().strip()
        if source:
            self._apply_folder_link(source)

    def _apply_folder_link(self, source_path):
        """Se houver um destino vinculado à origem, preenche automaticamente."""
        source_key = os.path.normpath(source_path)
        linked_dest = self.cfg.get("folder_links", {}).get(source_key, "")
        if linked_dest:
            self.var_dest.set(linked_dest)

    def _save_folder_link(self, source_path, dest_path):
        """Salva o vínculo entre pasta de origem e destino."""
        source_key = os.path.normpath(source_path)
        dest_val = os.path.normpath(dest_path)
        links = self.cfg.get("folder_links", {})
        links[source_key] = dest_val
        self.cfg["folder_links"] = links
        self._save_config()

    def _browse_source(self):
        folder = filedialog.askdirectory(title="Selecionar pasta de origem")
        if folder:
            self.var_path.set(folder)
            self._add_to_history(folder, "source")
            self._apply_folder_link(folder)

    def _browse_dest(self):
        folder = filedialog.askdirectory(title="Selecionar pasta de destino")
        if folder:
            self.var_dest.set(folder)
            self._add_to_history(folder, "dest")
            self.combo_dest["values"] = self.cfg["dest_history"]
            # Salvar vínculo origem→destino ao selecionar destino
            source = self.var_path.get().strip()
            if source:
                self._save_folder_link(source, folder)

    def _parse_datetime(self):
        try:
            date_str = self.date_entry.entry.get().strip()
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            hour = int(self.var_hour.get().strip())
            minute = int(self.var_minute.get().strip())
            return datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute)
        except (ValueError, AttributeError):
            Messagebox.show_error("Data/hora inválida.", title="Erro")
            return None

    def _parse_extensions(self, raw):
        exts = set()
        for e in raw.split(","):
            e = e.strip()
            if e and not e.startswith("."):
                e = "." + e
            if e:
                exts.add(e.lower())
        return exts

    def _parse_folder_list(self, raw):
        return {f.strip().lower() for f in raw.split(",") if f.strip()}

    def _format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _size_to_bytes(self, size_str):
        """Converte string de tamanho de volta para bytes para ordenação."""
        size_str = size_str.strip()
        try:
            if size_str.endswith(" B"):
                return float(size_str[:-2])
            elif size_str.endswith(" KB"):
                return float(size_str[:-3]) * 1024
            elif size_str.endswith(" MB"):
                return float(size_str[:-3]) * 1024 * 1024
            elif size_str.endswith(" GB"):
                return float(size_str[:-3]) * 1024 * 1024 * 1024
        except ValueError:
            pass
        return 0

    # --- Ordenação por coluna ---

    def _sort_by_column(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False

        # Atualizar cabeçalhos com indicador
        for c in ("nome", "pasta", "modificado", "tamanho"):
            base = {"nome": "Nome", "pasta": "Pasta", "modificado": "Modificado", "tamanho": "Tamanho"}[c]
            if c == col:
                arrow = " ▼" if self.sort_reverse else " ▲"
                self.tree.heading(c, text=base + arrow)
            else:
                self.tree.heading(c, text=base)

        # Ordenar dados
        if col == "nome":
            self.files_data.sort(key=lambda f: f["name"].lower(), reverse=self.sort_reverse)
        elif col == "pasta":
            self.files_data.sort(key=lambda f: f["folder"].lower(), reverse=self.sort_reverse)
        elif col == "modificado":
            self.files_data.sort(key=lambda f: f["modified"], reverse=self.sort_reverse)
        elif col == "tamanho":
            self.files_data.sort(key=lambda f: f["size"], reverse=self.sort_reverse)

        # Rebuild tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        for f in self.files_data:
            symbol = "☑" if f["selected"] else "☐"
            self.tree.insert("", "end", values=(
                symbol,
                f["name"],
                f["folder"],
                f["modified"].strftime("%d/%m/%Y %H:%M:%S"),
                self._format_size(f["size"])
            ))

    # --- Listagem ---

    def _list_files(self):
        source = self.var_path.get().strip()
        if not source or not os.path.isdir(source):
            Messagebox.show_warning("Selecione uma pasta de origem válida.", title="Aviso")
            return

        self._add_to_history(source, "source")
        self._save_config()

        cutoff = self._parse_datetime()
        if cutoff is None:
            return

        # Montar filtros de extensão
        ext_mode = self.var_ext_mode.get()
        ignored_exts = set()
        only_exts = set()
        if ext_mode == "Ignorar extensões":
            ignored_exts = self._parse_extensions(self.var_ext_value.get())
        elif ext_mode == "Somente essas extensões":
            only_exts = self._parse_extensions(self.var_ext_value.get())

        # Montar filtros de pasta
        folder_mode = self.var_folder_mode.get()
        ignored_folders = set()
        only_folders = set()
        if folder_mode == "Ignorar pastas":
            ignored_folders = self._parse_folder_list(self.var_folder_value.get())
        elif folder_mode == "Somente essas pastas":
            only_folders = self._parse_folder_list(self.var_folder_value.get())

        self._clear_tree()
        self.scanning = True
        self.sort_col = None
        self.sort_reverse = False
        self._log(f"Buscando em: {source}")
        self._log(f"Filtro: modificados após {cutoff.strftime('%d/%m/%Y %H:%M')}")

        def scan():
            found = []
            try:
                for dirpath, dirnames, filenames in os.walk(source):
                    if not self.scanning:
                        break
                    # Filtrar pastas
                    if ignored_folders:
                        dirnames[:] = [d for d in dirnames if d.lower() not in ignored_folders]
                    elif only_folders:
                        dirnames[:] = [d for d in dirnames if d.lower() in only_folders]

                    for fname in filenames:
                        if not self.scanning:
                            break
                        _, ext = os.path.splitext(fname)
                        ext_lower = ext.lower()

                        if only_exts and ext_lower not in only_exts:
                            continue
                        if ignored_exts and ext_lower in ignored_exts:
                            continue

                        filepath = os.path.join(dirpath, fname)
                        try:
                            stat = os.stat(filepath)
                            mtime = datetime.fromtimestamp(stat.st_mtime)
                            if mtime >= cutoff:
                                rel_dir = os.path.relpath(dirpath, source)
                                found.append({
                                    "name": fname,
                                    "folder": rel_dir,
                                    "full_path": filepath,
                                    "modified": mtime,
                                    "size": stat.st_size,
                                    "selected": True
                                })
                        except (OSError, PermissionError):
                            continue
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Erro: {e}"))

            self.root.after(0, lambda: self._populate_tree(found))

        threading.Thread(target=scan, daemon=True).start()

    def _populate_tree(self, files):
        self.scanning = False
        self.files_data = files

        for f in files:
            self.tree.insert("", "end", values=(
                "☑",
                f["name"],
                f["folder"],
                f["modified"].strftime("%d/%m/%Y %H:%M:%S"),
                self._format_size(f["size"])
            ))

        self.var_select_all.set(True)
        self._update_counter()
        self._log(f"Concluído: {len(files)} arquivo(s) encontrado(s)")

    def _toggle_check(self, event=None):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        for item_id in selected_items:
            idx = self.tree.index(item_id)
            if idx < len(self.files_data):
                self.files_data[idx]["selected"] = not self.files_data[idx]["selected"]
                symbol = "☑" if self.files_data[idx]["selected"] else "☐"
                values = list(self.tree.item(item_id, "values"))
                values[0] = symbol
                self.tree.item(item_id, values=values)
        self._update_counter()

    def _toggle_select_all(self):
        select = self.var_select_all.get()
        symbol = "☑" if select else "☐"
        for i, item_id in enumerate(self.tree.get_children()):
            if i < len(self.files_data):
                self.files_data[i]["selected"] = select
                values = list(self.tree.item(item_id, "values"))
                values[0] = symbol
                self.tree.item(item_id, values=values)
        self._update_counter()

    def _cancel_scan(self):
        self.scanning = False
        self._log("Busca cancelada")

    def _clear_all(self):
        self.scanning = False
        self._clear_tree()
        self.var_path.set("")
        self.date_entry.entry.delete(0, "end")
        self.date_entry.entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.var_hour.set("00")
        self.var_minute.set("00")
        self.txt_panel.configure(state="normal")
        self.txt_panel.delete("1.0", "end")
        self.txt_panel.configure(state="disabled")
        self.lbl_count.configure(text="Nenhum arquivo listado")
        self.progress["value"] = 0

    def _clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.files_data = []

    # --- Exportação ---

    def _cleanup_old_export_folders(self, dest):
        """Remove as pastas de exportação mais antigas, mantendo no máximo max_export_folders."""
        pattern = re.compile(r'^\d{8}_\d{6}$')
        max_folders = self.cfg.get("max_export_folders", 50)

        try:
            folders = [
                d for d in os.listdir(dest)
                if os.path.isdir(os.path.join(dest, d)) and pattern.match(d)
            ]
            folders.sort()  # Ordem cronológica pelo nome

            # -1 porque vamos criar uma nova pasta logo em seguida
            while len(folders) >= max_folders:
                oldest = folders.pop(0)
                shutil.rmtree(os.path.join(dest, oldest), ignore_errors=True)
                self._log(f"Pasta antiga removida: {oldest}")
        except Exception as e:
            self._log(f"Erro ao limpar pastas antigas: {e}")

    def _export(self):
        selected = [f for f in self.files_data if f["selected"]]
        if not selected:
            Messagebox.show_warning("Nenhum arquivo selecionado para exportar.", title="Aviso")
            return

        dest = self.var_dest.get().strip()
        if not dest:
            dest = filedialog.askdirectory(title="Selecionar pasta de destino para exportação")
            if not dest:
                return
            self.var_dest.set(dest)

        if not os.path.isdir(dest):
            os.makedirs(dest, exist_ok=True)

        self._add_to_history(dest, "dest")
        self.combo_dest["values"] = self.cfg["dest_history"]

        source = self.var_path.get().strip()
        if source:
            self._save_folder_link(source, dest)

        # Limpar pastas antigas de exportação antes de criar a nova
        self._cleanup_old_export_folders(dest)

        # Criar subpasta com timestamp YYYYMMDD_HHMMSS
        timestamp_folder = datetime.now().strftime('%Y%m%d_%H%M%S')
        dest = os.path.join(dest, timestamp_folder)
        os.makedirs(dest, exist_ok=True)

        gen_structure = self.var_gen_structure.get()
        gen_txt = self.var_gen_txt.get()
        export_zip = self.var_export_zip.get()

        total = len(selected)
        self.progress["maximum"] = total
        self.progress["value"] = 0

        def do_export():
            copied = 0
            errors = 0
            report_lines = []

            if export_zip:
                zip_name = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                zip_path = os.path.join(dest, zip_name)
                try:
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                        for i, f in enumerate(selected):
                            try:
                                if gen_structure:
                                    arcname = os.path.join(f["folder"], f["name"])
                                else:
                                    arcname = f["name"]
                                zf.write(f["full_path"], arcname)
                                copied += 1
                                report_lines.append(
                                    f"{f['folder']}\\{f['name']} | "
                                    f"{f['modified'].strftime('%d/%m/%Y %H:%M:%S')} | "
                                    f"{self._format_size(f['size'])}"
                                )
                            except Exception as e:
                                errors += 1
                                self.root.after(0, lambda e=e, n=f['name']: self._log(f"Erro ao compactar {n}: {e}"))
                            self.root.after(0, lambda v=i+1: self._set_progress(v))
                except Exception as e:
                    self.root.after(0, lambda: self._log(f"Erro ao criar ZIP: {e}"))
            else:
                for i, f in enumerate(selected):
                    try:
                        if gen_structure:
                            dest_dir = os.path.join(dest, f["folder"])
                        else:
                            dest_dir = dest

                        os.makedirs(dest_dir, exist_ok=True)
                        dest_path = os.path.join(dest_dir, f["name"])
                        shutil.copy2(f["full_path"], dest_path)
                        copied += 1
                        report_lines.append(
                            f"{f['folder']}\\{f['name']} | "
                            f"{f['modified'].strftime('%d/%m/%Y %H:%M:%S')} | "
                            f"{self._format_size(f['size'])}"
                        )
                    except Exception as e:
                        errors += 1
                        self.root.after(0, lambda e=e, n=f['name']: self._log(f"Erro ao copiar {n}: {e}"))
                    self.root.after(0, lambda v=i+1: self._set_progress(v))

            if gen_txt:
                try:
                    txt_path = os.path.join(dest, "resultado_exportacao.txt")
                    with open(txt_path, "w", encoding="utf-8") as tf:
                        tf.write(f"Exportação: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                        tf.write(f"Origem: {source}\n")
                        tf.write(f"Destino: {dest}\n")
                        tf.write(f"Total: {copied} arquivo(s)\n")
                        if export_zip:
                            tf.write(f"ZIP: {zip_name}\n")
                        tf.write("-" * 80 + "\n")
                        for line in report_lines:
                            tf.write(line + "\n")
                except Exception as e:
                    self.root.after(0, lambda: self._log(f"Erro ao gerar txt: {e}"))

            mode = "compactado(s)" if export_zip else "copiado(s)"
            self.root.after(0, lambda: self._log(f"Exportação: {copied} {mode}, {errors} erro(s) → {dest}"))
            self.root.after(0, lambda: Messagebox.show_info(
                f"{copied} arquivo(s) exportado(s) com sucesso!\n\nDestino: {dest}",
                title="Exportação concluída"
            ))

        threading.Thread(target=do_export, daemon=True).start()

    def _set_progress(self, value):
        self.progress["value"] = value


if __name__ == "__main__":
    saved_theme = "cosmo"
    try:
        with open(_get_config_path(), "r", encoding="utf-8") as f:
            saved_theme = json.load(f).get("theme", "cosmo")
    except Exception:
        pass
    app = ttk.Window(themename=saved_theme)
    FileSelector(app)
    app.mainloop()
