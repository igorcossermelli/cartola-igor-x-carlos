# Igor x Carlos no Cartola

Comparação entre Igor Pro F.C e RB Papai no Cartola FC, temporada a temporada.

Site: https://igorcossermelli.github.io/cartola-igor-x-carlos/

## Como funciona

O GitHub Actions roda `build/montar.py` a cada 3 horas. O script baixa os dados da API pública do Cartola, recalcula tudo e gera `index.html` e `og.png` (a imagem de prévia do link). Só há commit quando algo mudou.

Para rodar à mão: aba **Actions** > **Atualizar site** > **Run workflow**.

## Temporadas

A API do Cartola só tem a temporada atual, então cada temporada fica guardada em `build/arquivo/<ano>.json`, atualizada a cada rodada. Não apague essa pasta: é o único lugar onde as temporadas antigas existem.

- Durante o campeonato, a página principal mostra a temporada atual.
- Na pré-temporada, quando ainda não há rodada pontuada, a página principal mostra a última temporada guardada, com um aviso.
- Quando a temporada seguinte começa, as anteriores ganham uma página própria em `temporadas/<ano>/`, e o topo do site mostra um seletor de ano.

Para montar localmente:

```
pip install pillow==11.3.0
python build/montar.py --forcar
```

A fonte Barlow Condensed está em `build/fontes/` sob a licença SIL Open Font License (`OFL.txt`).
