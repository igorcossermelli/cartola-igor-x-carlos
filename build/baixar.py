# -*- coding: utf-8 -*-
# Baixa da API publica do Cartola tudo o que o site usa, ate a ultima rodada ja pontuada.
# Uso: python baixar.py <pasta_dados>   (imprime o numero da ultima rodada)
import json, os, sys, time, urllib.request

API = 'https://api.cartolafc.globo.com'
TIMES = ['15426262', '4503052']  # RB Papai (Carlos), Igor Pro F.C (Igor)
PASTA = sys.argv[1]


def get(caminho):
    erro = None
    for tentativa in range(4):
        try:
            req = urllib.request.Request(API + caminho, headers={
                'User-Agent': 'cartola-igor-x-carlos (+https://github.com/igorcossermelli/cartola-igor-x-carlos)',
                'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            erro = e
            time.sleep(3 * (tentativa + 1))
    raise RuntimeError('Falha ao baixar %s: %s' % (caminho, erro))


def salvar(nome, dados):
    # A API devolve os atletas em ordem diferente a cada consulta; ordenar deixa o build reproduzivel.
    if isinstance(dados, dict):
        for chave in ('atletas', 'reservas'):
            if isinstance(dados.get(chave), list):
                dados[chave] = sorted(dados[chave], key=lambda a: a.get('atleta_id', 0))
    caminho = os.path.join(PASTA, nome)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False)


status = get('/mercado/status')
# A rodada atual e a que esta aberta ou em andamento; a ultima pontuada e a anterior,
# a nao ser que o campeonato ja tenha terminado.
ultima = int(os.environ.get("TOTAL_RODADAS", "38")) if status.get("game_over") else status['rodada_atual'] - 1
salvar('status.json', status)
salvar('clubes.json', get('/clubes'))
salvar('esquemas.json', get('/esquemas'))
salvar('rodadas_cal.json', get('/rodadas'))
for r in range(1, ultima + 1):
    salvar('pontuados/%d.json' % r, get('/atletas/pontuados/%d' % r))
    for t in TIMES:
        salvar('%s_%d.json' % (t, r), get('/time/id/%s/%d' % (t, r)))
print(ultima)
