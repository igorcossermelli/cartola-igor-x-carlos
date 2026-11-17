# Igor x Carlos no Cartola 2026

Comparação entre Igor Pro F.C e RB Papai no Cartola FC 2026.

Site: https://igorcossermelli.github.io/cartola-igor-x-carlos/

## Como funciona

O GitHub Actions roda `build/montar.py` a cada 3 horas. O script baixa os dados da API pública do Cartola, recalcula tudo e gera `index.html` e `og.png` (a imagem de prévia do link). Só há commit quando algo mudou.

Para rodar à mão: aba **Actions** > **Atualizar site** > **Run workflow**.

Para montar localmente:

```
pip install pillow==11.3.0
python build/montar.py --forcar
```

A fonte Barlow Condensed está em `build/fontes/` sob a licença SIL Open Font License (`OFL.txt`).
