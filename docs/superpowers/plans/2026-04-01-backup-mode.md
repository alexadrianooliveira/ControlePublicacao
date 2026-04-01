# Modo Backup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backup mode to FileSelector — generate a JSON structure file on export and allow scanning a directory using that JSON to find matching files for backup.

**Architecture:** Two changes to `file_selector.py`: (1) export always generates `[folder_structure].json`, (2) new tab inside Filters card with a file picker for the JSON that bypasses all normal filters during scan.

**Tech Stack:** Python 3.12, ttkbootstrap, tkinter, json, os, threading

**Spec:** `docs/superpowers/specs/2026-04-01-backup-mode-design.md`

---

## File Structure

Only one file is modified: `file_selector.py` (~857 lines).

Changes by area:
- **`_build_ui()`** (line 134-331): Wrap filter widgets in a Notebook with two tabs
- **`_list_files()`** (line 533-615): Add branch for backup mode scan
- **`do_export()`** inside `_export()` (line 768-842): Generate JSON after copying files
- **New methods**: `_browse_structure()`, `_clear_structure()`, `_scan_from_structure()`, `_generate_folder_structure_json()`

---

## Task 1: Generate `[folder_structure].json` on export

**Files:**
- Modify: `file_selector.py:768-842` (inside `do_export()`)

- [ ] **Step 1: Add `_generate_folder_structure_json()` method**

Add this method to the `FileSelector` class, before `_set_progress()` (line 844):

```python
def _generate_folder_structure_json(self, dest, source, report_lines, selected):
    """Gera [folder_structure].json na pasta de exportacao."""
    try:
        structure = {
            "source": source,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "files": [
                {"name": f["name"], "folder": f["folder"]}
                for f in selected
            ]
        }
        json_path = os.path.join(dest, "[folder_structure].json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(structure, jf, ensure_ascii=False, indent=2)
        self.root.after(0, lambda: self._log("Estrutura de arquivos salva: [folder_structure].json"))
    except Exception as e:
        self.root.after(0, lambda: self._log(f"Erro ao gerar [folder_structure].json: {e}"))
```

- [ ] **Step 2: Call it from `do_export()`**

Inside `do_export()`, after the `if gen_txt:` block (after line 833) and before the final log/messagebox (line 835), add:

```python
self._generate_folder_structure_json(dest, source, report_lines, selected)
```

Note: `source` is already captured at line 744 and `selected` at line 726 — both are accessible in `do_export()` closure.

- [ ] **Step 3: Test manually**

Run `python file_selector.py`, select a source folder, list files, export. Verify:
- `[folder_structure].json` exists inside the `[ULTIMO]_YYYYMMDD_HHMMSS` folder
- JSON contains `source`, `exported_at`, and `files` array with correct `name`/`folder` entries
- Log panel shows "Estrutura de arquivos salva: [folder_structure].json"

- [ ] **Step 4: Commit**

```bash
git add file_selector.py
git commit -m "feat: gerar [folder_structure].json automaticamente na exportacao"
```

---

## Task 2: Add Notebook tabs inside Filters card

**Files:**
- Modify: `file_selector.py:171-221` (`_build_ui()`, filters section)

- [ ] **Step 1: Wrap existing filter widgets in a Notebook**

Replace the filters section (lines 171-221) in `_build_ui()`. The `card_filters` Labelframe stays, but its children are now inside a Notebook.

Current code to replace — from `# === FILTROS ===` to end of `row_date` widgets (line 221):

```python
        # === FILTROS ===
        card_filters = ttk.Labelframe(main, text="  Filtros  ", padding=10, bootstyle="info")
        card_filters.pack(fill=X, pady=(0, 8))

        self.notebook_filters = ttk.Notebook(card_filters, bootstyle="info")
        self.notebook_filters.pack(fill=X)

        # --- Aba Filtros ---
        tab_filters = ttk.Frame(self.notebook_filters, padding=8)
        self.notebook_filters.add(tab_filters, text="  Filtros  ")

        # Linha 1: Extensões
        row_ext = ttk.Frame(tab_filters)
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
        row_folder = ttk.Frame(tab_filters)
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
        row_date = ttk.Frame(tab_filters)
        row_date.pack(fill=X)

        ttk.Label(row_date, text="A partir de:", font=("-size", 9, "-weight", "bold"), width=10).pack(side=LEFT)
```

Note: the `row_ext`, `row_folder`, and `row_date` frames now use `tab_filters` as parent instead of `card_filters`. The remaining date widgets (DateEntry, Spinboxes on lines 212-221) continue unchanged — they already pack into `row_date`.

- [ ] **Step 2: Add the "Estrutura de arquivos" tab**

Right after the date widgets and before `# === BOTOES DE ACAO ===`, add:

```python
        # --- Aba Estrutura de arquivos ---
        tab_structure = ttk.Frame(self.notebook_filters, padding=8)
        self.notebook_filters.add(tab_structure, text="  Estrutura de arquivos  ")

        row_structure = ttk.Frame(tab_structure)
        row_structure.pack(fill=X)

        ttk.Label(row_structure, text="Arquivo:", font=("-size", 9, "-weight", "bold"), width=10).pack(side=LEFT)
        self.var_structure_file = ttk.StringVar()
        self.entry_structure = ttk.Entry(row_structure, textvariable=self.var_structure_file,
                                          font=("-size", 9), state="readonly")
        self.entry_structure.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))
        ttk.Button(row_structure, text="Procurar...", command=self._browse_structure,
                   bootstyle="info-outline").pack(side=LEFT, padx=(0, 4))
        ttk.Button(row_structure, text="Limpar", command=self._clear_structure,
                   bootstyle="warning-outline").pack(side=LEFT)
```

- [ ] **Step 3: Add `_browse_structure()` and `_clear_structure()` methods**

Add these after `_browse_dest()` (line 437):

```python
    def _browse_structure(self):
        filepath = filedialog.askopenfilename(
            title="Selecionar arquivo de estrutura",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")]
        )
        if filepath:
            self.var_structure_file.set(filepath)

    def _clear_structure(self):
        self.var_structure_file.set("")
```

- [ ] **Step 4: Test manually**

Run `python file_selector.py`. Verify:
- Card "Filtros" now has two tabs: "Filtros" and "Estrutura de arquivos"
- Existing filters tab looks and works exactly the same
- Structure tab has the file picker and clear button
- Browse opens file dialog filtered to JSON
- Clear empties the field

- [ ] **Step 5: Commit**

```bash
git add file_selector.py
git commit -m "feat: adicionar abas Filtros e Estrutura de arquivos no card Filtros"
```

---

## Task 3: Implement backup scan mode in `_list_files()`

**Files:**
- Modify: `file_selector.py:533-615` (`_list_files()`)

- [ ] **Step 1: Add `_is_backup_mode()` helper**

Add after `_clear_structure()`:

```python
    def _is_backup_mode(self):
        """Retorna True se a aba Estrutura de arquivos esta ativa e um JSON foi selecionado."""
        active_tab = self.notebook_filters.index(self.notebook_filters.select())
        return active_tab == 1 and self.var_structure_file.get().strip()
```

- [ ] **Step 2: Add `_load_structure_file()` method**

Add after `_is_backup_mode()`:

```python
    def _load_structure_file(self, filepath):
        """Le e valida o JSON de estrutura. Retorna lista de files ou None se invalido."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            Messagebox.show_error(f"Erro ao ler arquivo de estrutura:\n{e}", title="Erro")
            return None

        if not isinstance(data.get("files"), list):
            Messagebox.show_error("Arquivo JSON invalido: chave 'files' ausente ou nao e uma lista.", title="Erro")
            return None

        for i, entry in enumerate(data["files"]):
            if not isinstance(entry, dict) or "name" not in entry or "folder" not in entry:
                Messagebox.show_error(
                    f"Arquivo JSON invalido: entrada {i} deve ter 'name' e 'folder'.",
                    title="Erro"
                )
                return None

        return data["files"]
```

- [ ] **Step 3: Modify `_list_files()` to branch on backup mode**

In `_list_files()`, after the source validation and `_add_to_history` call (lines 533-540), add the backup mode branch. The modified method becomes:

```python
    def _list_files(self):
        source = self.var_path.get().strip()
        if not source or not os.path.isdir(source):
            Messagebox.show_warning("Selecione uma pasta de origem valida.", title="Aviso")
            return

        self._add_to_history(source, "source")
        self._save_config()

        # --- Modo backup (estrutura de arquivos) ---
        if self._is_backup_mode():
            structure_file = self.var_structure_file.get().strip()
            file_list = self._load_structure_file(structure_file)
            if file_list is None:
                return

            self._clear_tree()
            self.scanning = True
            self.sort_col = None
            self.sort_reverse = False
            self._log(f"Modo backup: buscando {len(file_list)} arquivo(s) em: {source}")

            def scan_structure():
                found = []
                not_found = 0
                for entry in file_list:
                    if not self.scanning:
                        break
                    filepath = os.path.join(source, entry["folder"], entry["name"])
                    filepath = os.path.normpath(filepath)
                    try:
                        stat = os.stat(filepath)
                        mtime = datetime.fromtimestamp(stat.st_mtime)
                        rel_dir = entry["folder"]
                        found.append({
                            "name": entry["name"],
                            "folder": rel_dir,
                            "full_path": filepath,
                            "modified": mtime,
                            "size": stat.st_size,
                            "selected": True
                        })
                    except (FileNotFoundError, OSError):
                        not_found += 1
                        name_display = f"{entry['folder']}\\{entry['name']}"
                        self.root.after(0, lambda n=name_display: self._log(f"Nao encontrado: {n}"))

                if not_found:
                    self.root.after(0, lambda nf=not_found: self._log(
                        f"Atencao: {nf} arquivo(s) nao encontrado(s) na origem"
                    ))
                self.root.after(0, lambda: self._populate_tree(found))

            threading.Thread(target=scan_structure, daemon=True).start()
            return

        # --- Modo normal (filtros) ---
        cutoff = self._parse_datetime()
        if cutoff is None:
            return
        # ... rest of existing code unchanged ...
```

The key change: the backup branch returns early after launching its thread, so the normal filter code is never reached.

- [ ] **Step 4: Test manually**

1. Export some files to generate a `[folder_structure].json` (from Task 1)
2. Switch to "Estrutura de arquivos" tab, select the JSON
3. Set a source folder that contains matching files
4. Click "Listar arquivos"
5. Verify: matching files appear in the tree, non-matching files show in the log
6. Export works normally from the listed files

- [ ] **Step 5: Test edge cases**

- Select a malformed JSON (e.g., `{}`) — should show error dialog
- Select a JSON with files that don't exist in source — should log "Nao encontrado" for each
- Switch back to "Filtros" tab — normal scan should work as before
- Cancel during backup scan — should stop

- [ ] **Step 6: Commit**

```bash
git add file_selector.py
git commit -m "feat: implementar scan no modo backup usando JSON de estrutura"
```

---

## Task 4: Final integration test and cleanup

- [ ] **Step 1: Full end-to-end test**

1. Run FileSelector, select a source with files, list, export
2. Confirm `[folder_structure].json` is in the export folder
3. Open a second instance pointing to a different "source" (simulating the server)
4. Load the JSON in the "Estrutura de arquivos" tab
5. List — should find matching files
6. Export — backup is created with the correct structure

- [ ] **Step 2: Commit final state**

```bash
git add file_selector.py
git commit -m "feat: modo backup completo - gerar JSON na exportacao e scan por estrutura"
```
