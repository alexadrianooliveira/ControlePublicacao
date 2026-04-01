# ControlePublicacao - File Selector

Aplicacao desktop desenvolvida em Python com ttkbootstrap para selecionar e exportar arquivos modificados apos uma data/hora especifica, mantendo a estrutura de pastas original.

## Funcionalidades

- Selecao de arquivos modificados a partir de uma data/hora
- Exportacao mantendo a estrutura de pastas original
- Filtros por extensao e pasta
- Compactacao em .zip
- Geracao de relatorio .txt
- Historico de pastas de origem e destino
- Vinculo automatico entre pastas de origem e destino
- Controle de quantidade maxima de subpastas de exportacao
- Interface grafica com temas (ttkbootstrap)

## Requisitos

- Python 3.x
- ttkbootstrap

## Como executar

```bash
python file_selector.py
```

## Build (gerar executavel)

```bash
python -m PyInstaller FileSelector.spec --distpath dist --clean
```

O executavel sera gerado em `dist/FileSelector.exe`.

## Configuracao

As configuracoes sao salvas automaticamente em `file_selector_config.json` ao lado do executavel, incluindo historico de pastas, filtros e tema selecionado.
