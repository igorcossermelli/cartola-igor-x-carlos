# -*- coding: utf-8 -*-
# Comparacoes extras: scouts, custo-beneficio, Palmeiras, time ideal e projecao final.
# Uso: ULTIMA=<rodada> python extras.py <pasta_dados> <site_data.json>  (acrescenta a chave "extras" no JSON)
import io, json, os, random, sys
from collections import defaultdict

D, DATA = sys.argv[1], sys.argv[2]
ULTIMA = int(os.environ.get('ULTIMA', '34'))
RODADAS = list(range(1, ULTIMA + 1))
TIMES = [('carlos', '15426262'), ('igor', '4503052')]
POS = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
POS_KEY = {1: 'gol', 2: 'lat', 3: 'zag', 4: 'mei', 5: 'ata', 6: 'tec'}
RESTANTES = 38 - ULTIMA


def load(name):
    with io.open('%s/%s' % (D, name), encoding='utf-8') as f:
        return json.load(f)


def r2(x):
    return round(x, 2)

clubes = load('clubes.json')
esquemas = load('esquemas.json')


def clube(cid):
    c = clubes.get(str(cid))
    return c.get('abreviacao') if c else ''

with io.open(DATA, encoding='utf-8') as f:
    out = json.load(f)

# ---- Time ideal de cada rodada (sem limite de cartoletas) ----
ideal = {}
for r in RODADAS:
    p = load('pontuados/%d.json' % r)
    por_pos = defaultdict(list)
    for aid, a in p['atletas'].items():
        if a.get('entrou_em_campo') is False:
            continue
        por_pos[POS_KEY.get(a['posicao_id'])].append((a['pontuacao'], a['apelido']))
    for k in por_pos:
        por_pos[k].sort(reverse=True)
    melhor = None
    for e in esquemas:
        soma, linha = 0.0, []
        ok = True
        for k, n in e['posicoes'].items():
            if len(por_pos[k]) < n:
                ok = False
                break
            escolhidos = por_pos[k][:n]
            soma += sum(x[0] for x in escolhidos)
            if k != 'tec':
                linha += escolhidos
        if not ok:
            continue
        cap = max(linha)
        total = soma + 0.5 * cap[0]
        if melhor is None or total > melhor['pts']:
            melhor = {'pts': r2(total), 'esquema': e['nome'], 'capitao': cap[1], 'capitao_pts': r2(cap[0])}
    maior = max((a for a in p['atletas'].values() if a['posicao_id'] != 6), key=lambda a: a['pontuacao'])
    melhor['destaque'] = maior['apelido']
    melhor['destaque_pts'] = r2(maior['pontuacao'])
    melhor['destaque_id'] = int([k for k, v in p['atletas'].items() if v is maior][0])
    ideal[r] = melhor

extras = {'ideal': [dict(rodada=r, **ideal[r]) for r in RODADAS], 'times': {}, 'escalacoes': {}}


def escalado(a, d):
    """Formato curto de um atleta para o explorador de rodada."""
    return {'i': a['atleta_id'], 'n': a.get('apelido_abreviado') or a['apelido'], 'p': POS[a['posicao_id']],
            'c': clube(a['clube_id']), 'pts': r2(a['pontos_num']), 'cap': a['atleta_id'] == d.get('capitao_id'),
            'lux': a['atleta_id'] == d.get('reserva_luxo_id'), 'jogou': bool(a.get('entrou_em_campo'))}

for key, tid in TIMES:
    t = out['times'][key]
    gols, assist = defaultdict(lambda: [None, 0]), defaultdict(lambda: [None, 0])
    sc_tot = defaultdict(int)
    custo_rod, pts_rod = [], []
    jog = {}
    pal = {'escalacoes': 0, 'pts': 0.0, 'capitao': 0, 'capitao_pts': 0.0, 'jogadores': {}, 'rodadas_com': 0}
    aprov = []
    teve_destaque = 0
    escalacoes = []
    for r in RODADAS:
        d = load('%s_%d.json' % (tid, r))
        at = d['atletas']
        escalacoes.append({'r': r, 'esquema': next((e['nome'] for e in esquemas if e['esquema_id'] == d.get('esquema_id')), '?'),
                           'pts': r2(d['pontos']), 'atletas': [escalado(a, d) for a in at],
                           'banco': [escalado(a, d) for a in d.get('reservas') or []]})
        custo = 0.0
        tem_pal = False
        ids = set()
        for a in at:
            ids.add(a['atleta_id'])
            s = a.get('scout') or {}
            for k, v in s.items():
                sc_tot[k] += v
            if s.get('G'):
                gols[a['atleta_id']][0] = a['apelido']
                gols[a['atleta_id']][1] += s['G']
            if s.get('A'):
                assist[a['atleta_id']][0] = a['apelido']
                assist[a['atleta_id']][1] += s['A']
            # preco_num e o preco depois da rodada; o preco pago e preco - variacao
            pago = a['preco_num'] - (a.get('variacao_num') or 0)
            custo += pago
            j = jog.setdefault(a['atleta_id'], {'nome': a['apelido'], 'pos': POS[a['posicao_id']], 'clube': clube(a['clube_id']),
                                                 'jogos': 0, 'pts': 0.0, 'gasto': 0.0})
            j['jogos'] += 1
            j['pts'] += a['pontos_num']
            j['gasto'] += pago
            if clube(a['clube_id']) == 'PAL':
                tem_pal = True
                pal['escalacoes'] += 1
                pal['pts'] += a['pontos_num']
                pj = pal['jogadores'].setdefault(a['apelido'], {'nome': a['apelido'], 'pos': POS[a['posicao_id']], 'jogos': 0, 'pts': 0.0})
                pj['jogos'] += 1
                pj['pts'] += a['pontos_num']
                if a['atleta_id'] == d.get('capitao_id'):
                    pal['capitao'] += 1
                    pal['capitao_pts'] += a['pontos_num']
        if tem_pal:
            pal['rodadas_com'] += 1
        custo_rod.append(r2(custo))
        pts_rod.append(d['pontos'])
        aprov.append(r2(100 * d['pontos'] / ideal[r]['pts']))
        if ideal[r]['destaque_id'] in ids:
            teve_destaque += 1

    def top(dct, n=3):
        return [{'nome': v[0], 'n': v[1]} for v in sorted(dct.values(), key=lambda v: -v[1])[:n]]

    jl = []
    for j in jog.values():
        if j['gasto'] > 0:
            j['preco_medio'] = r2(j['gasto'] / j['jogos'])
            j['pts'] = r2(j['pts'])
            j['pts_por_c'] = r2(j['pts'] / j['gasto'])
            j['media'] = r2(j['pts'] / j['jogos'])
            jl.append(j)
    fixos = [j for j in jl if j['jogos'] >= 3]
    caros = [j for j in fixos if j['preco_medio'] >= 12]
    pal_j = sorted(({'nome': v['nome'], 'pos': v['pos'], 'jogos': v['jogos'], 'pts': r2(v['pts']), 'media': r2(v['pts'] / v['jogos'])}
                    for v in pal['jogadores'].values()), key=lambda j: -j['pts'])
    extras['escalacoes'][key] = escalacoes
    extras['times'][key] = {
        'scouts': {
            'gols': sc_tot.get('G', 0), 'assist': sc_tot.get('A', 0), 'sg': sc_tot.get('SG', 0), 'defesas': sc_tot.get('DE', 0),
            'desarmes': sc_tot.get('DS', 0), 'amarelos': sc_tot.get('CA', 0), 'vermelhos': sc_tot.get('CV', 0),
            'gols_contra': sc_tot.get('GC', 0), 'penaltis_perdidos': sc_tot.get('PP', 0),
            'artilheiros': top(gols), 'garcons': top(assist),
        },
        'custo': {
            'por_rodada': custo_rod, 'total': r2(sum(custo_rod)), 'medio': r2(sum(custo_rod) / len(custo_rod)),
            'pts_por_c': r2(sum(pts_rod) / sum(custo_rod)),
            'melhores': sorted(fixos, key=lambda j: -j['pts_por_c'])[:5],
            'decepcoes': sorted(caros, key=lambda j: j['pts_por_c'])[:3],
        },
        'palmeiras': {
            'escalacoes': pal['escalacoes'], 'pts': r2(pal['pts']), 'media': r2(pal['pts'] / pal['escalacoes']) if pal['escalacoes'] else 0,
            'share': r2(100 * pal['pts'] / t['total']), 'rodadas_com': pal['rodadas_com'],
            'capitao': pal['capitao'], 'capitao_pts': r2(pal['capitao_pts']), 'jogadores': pal_j[:8],
        },
        'ideal': {
            'aprov': aprov, 'media': r2(sum(aprov) / len(aprov)), 'melhor': max(aprov), 'melhor_r': RODADAS[aprov.index(max(aprov))],
            'pior': min(aprov), 'pior_r': RODADAS[aprov.index(min(aprov))], 'teve_destaque': teve_destaque,
        },
    }

# ---- Projecao das rodadas 35 a 38 ----
# Sorteia, para cada rodada que falta, uma das 34 rodadas ja jogadas e repete a diferenca daquela rodada
# (Igor menos Carlos). Sortear a mesma rodada para os dois mantem o efeito de rodada boa ou ruim para todo mundo.
c, i = out['times']['carlos'], out['times']['igor']
diffs = [b['pontos'] - a['pontos'] for a, b in zip(c['rodadas'], i['rodadas'])]
vantagem = i['total'] - c['total']
rng = random.Random(2026)
N = 200000
finais = []
virou = 0
for _ in range(N):
    g = vantagem + sum(rng.choice(diffs) for _ in range(RESTANTES))
    finais.append(g)
    if g < 0:
        virou += 1
finais.sort()
melhor_c4 = sorted(diffs)[:RESTANTES]
extras['projecao'] = {
    'vantagem': r2(vantagem), 'restantes': RESTANTES, 'simulacoes': N,
    'chance_carlos': r2(100 * virou / N), 'chance_igor': r2(100 * (N - virou) / N),
    'mediana': r2(finais[N // 2]), 'p10': r2(finais[N // 10]), 'p90': r2(finais[9 * N // 10]),
    'carlos_precisa_por_rodada': r2(vantagem / RESTANTES) if RESTANTES else None,
    'carlos_melhor_vantagem_rodada': r2(-min(diffs)),
    'rodadas_carlos_mais_22': sum(1 for d in diffs if -d > vantagem / RESTANTES) if RESTANTES else None,
    'soma_4_melhores_carlos': r2(-sum(melhor_c4)),
    'hist': [],
}
# Histograma da vantagem final do Igor, em faixas de 20 pontos
lo = int((finais[0] // 20) * 20)
hi = int((finais[-1] // 20 + 1) * 20)
for b in range(lo, hi, 20):
    n = sum(1 for g in finais if b <= g < b + 20)
    extras['projecao']['hist'].append({'de': b, 'ate': b + 20, 'pct': r2(100 * n / N)})

out['extras'] = extras
with io.open(DATA, 'w', encoding='utf-8') as f:
    f.write(json.dumps(out, ensure_ascii=False))
