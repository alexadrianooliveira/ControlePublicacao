# ProductMaker - File Selector

## Visao Geral
Aplicacao desktop (Python + ttkbootstrap) para selecionar e exportar arquivos modificados apos uma data/hora especifica, mantendo a estrutura de pastas original.

## Estrutura do Projeto
- `file_selector.py` — codigo principal (UI + logica de exportacao)
- `FileSelector.spec` — spec do PyInstaller para gerar o .exe
- `file_selector.ico` — icone da aplicacao
- `file_selector_config.json` — config persistido (gerado em runtime)
- `dist/FileSelector.exe` — executavel gerado

## Build
```bash
python -m PyInstaller FileSelector.spec --distpath dist --clean
```

## Configuracao
Salva em `file_selector_config.json` ao lado do executavel. Campos principais:
- `source_history` / `dest_history` — historico de pastas
- `folder_links` — vinculo automatico origem -> destino
- `ext_mode` / `folder_mode` — filtros de extensao e pasta
- `max_export_folders` — maximo de subpastas de exportacao no destino (padrao: 50)
- `theme` — tema ttkbootstrap

## Comportamento de Exportacao
- Arquivos sao salvos em subpasta com timestamp `YYYYMMDD_HHMMSS` dentro do destino
- Antes de cada exportacao, pastas antigas nesse formato sao removidas para manter no maximo `max_export_folders` pastas
- Opcoes: manter estrutura de pastas, gerar relatorio .txt, compactar em .zip
- O parametro `max_export_folders` e configuravel pela UI (Spinbox) e persistido no config JSON

## Convencoes
- Idioma da UI: portugues (BR)
- Logs no painel inferior com timestamp `[HH:MM:SS]`
- Exportacao roda em thread separada para nao travar a UI
- Paths normalizados com `os.path.normpath`
