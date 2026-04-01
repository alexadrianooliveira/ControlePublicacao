# Modo Backup — Estrutura de Arquivos

**Data:** 2026-04-01
**Status:** Aprovado

## Problema

O usuario exporta arquivos modificados com o FileSelector e depois sobe manualmente pro servidor FTP. Antes de subir, precisa fazer backup dos arquivos que serao substituidos no servidor. Hoje esse processo e manual.

## Solucao

Duas alteracoes no FileSelector:

1. **Gerar JSON de estrutura na exportacao** — sempre que exportar, criar um `[folder_structure].json` na raiz da pasta timestamped com a lista de arquivos exportados.
2. **Modo "Estrutura de arquivos"** — nova aba dentro do card Filtros que permite selecionar um JSON gerado anteriormente. Ao listar, ignora todos os filtros normais e busca na pasta de origem os arquivos correspondentes.

## Design detalhado

### 1. JSON de estrutura (`[folder_structure].json`)

Gerado automaticamente dentro da pasta `[ULTIMO]_YYYYMMDD_HHMMSS` ao final de cada exportacao (tanto copia quanto zip). Formato:

```json
{
  "source": "D:\\Projetos\\MeuApp",
  "exported_at": "2026-04-01T14:30:00",
  "files": [
    { "name": "index.php", "folder": "www\\pages" },
    { "name": "style.css", "folder": "www\\assets\\css" }
  ]
}
```

- `source`: pasta de origem usada na exportacao (campo informativo — nao e usado para validacao, pois no servidor a origem sera diferente)
- `exported_at`: timestamp ISO da exportacao
- `files`: lista com `name` (nome do arquivo) e `folder` (caminho relativo da pasta, igual ao campo "pasta" da Treeview). Quando o arquivo esta na raiz da origem, `folder` sera `"."`

O JSON e gerado DEPOIS da copia/zip dos arquivos, dentro da funcao `do_export()` na thread de exportacao.

### 2. UI — Abas dentro do card "Filtros"

O `ttk.Labelframe` "Filtros" (variavel `card_filters`, linha ~172) passa a conter um `ttk.Notebook` com duas abas:

- **Aba "Filtros"** — contem exatamente os mesmos widgets que existem hoje (extensoes, pastas, data/hora). Nenhuma alteracao.
- **Aba "Estrutura de arquivos"** — contem:
  - Label "Arquivo de estrutura:"
  - Entry (readonly) mostrando o caminho do JSON selecionado (`self.var_structure_file`)
  - Botao "Procurar..." que abre `filedialog.askopenfilename` filtrando `*.json`
  - Botao "Limpar" que remove a selecao

Nova variavel de estado: `self.var_structure_file` (StringVar, vazio por padrao).

### 3. Comportamento do scan no modo backup

No metodo `_list_files()`, antes de montar os filtros normais, verificar:

```python
active_tab = self.notebook_filters.index(self.notebook_filters.select())
structure_file = self.var_structure_file.get().strip()
```

**Se a aba ativa for "Estrutura de arquivos" E houver um JSON selecionado:**
- Pular completamente `_parse_datetime()` e todos os filtros de extensao, pasta e data
- Ler o JSON e validar: deve conter a chave `files` como lista, e cada entry deve ter `name` e `folder`. Se o JSON for invalido ou malformado, exibir `Messagebox.show_error()` com mensagem amigavel e abortar
- Para cada entry `{ name, folder }`:
  - Construir o caminho esperado: `os.path.join(source, folder, name)` (funciona corretamente mesmo quando `folder` e `"."`)
  - Se o arquivo existir: adicionar ao `found[]` com os dados reais (stat)
  - Se nao existir: logar `[HH:MM:SS] Nao encontrado: folder\name`
- A populacao da Treeview e o fluxo de exportacao continuam identicos

**Se a aba ativa for "Filtros":**
- Comportamento 100% identico ao atual, sem nenhuma mudanca

### 4. Arquivos impactados

Apenas `file_selector.py`:

- `_build_ui()`: criar Notebook dentro do card_filters, mover widgets existentes pra aba "Filtros", criar aba "Estrutura de arquivos"
- `_list_files()`: adicionar branch para modo backup no inicio
- `do_export()` (dentro de `_export()`): gerar o JSON apos copiar/compactar arquivos
- Novos metodos auxiliares: `_browse_structure()`, `_clear_structure()`

### 5. Config

Nenhuma nova chave no JSON de config. O caminho do arquivo de estrutura e transiente (nao persiste entre sessoes).

### 6. Fluxo completo

```
Maquina local:
  FileSelector → aba Filtros → lista + exporta
  → pasta [ULTIMO]_20260401_143000/
      ├── www/pages/index.php
      ├── www/assets/css/style.css
      ├── resultado_exportacao.txt (se habilitado)
      └── [folder_structure].json         ← NOVO

Servidor:
  FileSelector.exe → aba "Estrutura de arquivos"
  → seleciona [folder_structure].json
  → Origem: C:\inetpub\wwwroot
  → "Listar arquivos" → encontra os arquivos correspondentes
  → Exporta → backup salvo em pasta timestamped
  → Usuario sobe os arquivos novos com seguranca
```
