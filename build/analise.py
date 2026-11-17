# -*- coding: utf-8 -*-
# Analise Cartola: Carlos (RB Papai) x Igor (Igor Pro F.C), da rodada 1 ate a ultima pontuada.
# Uso: ULTIMA=<rodada> python analise.py <pasta_dados> <saida.json>
from __future__ import division
import io, json, os, sys
from collections import defaultdict

D, OUT = sys.argv[1], sys.argv[2]
RODADAS = list(range(1, int(os.environ.get('ULTIMA', '34')) + 1))
TIMES = [('carlos', '15426262', 'Carlos', 'RB Papai'), ('igor', '4503052', 'Igor', 'Igor Pro F.C')]
POS = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}
SETOR = {1: 'gol', 2: 'def', 3: 'def', 4: 'mei', 5: 'ata', 6: 'tec'}
MESES = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def load(name):
    with io.open('%s/%s' % (D, name), encoding='utf-8') as f:
        return json.load(f)

clubes = load('clubes.json')
esquemas = dict((e['esquema_id'], e['nome']) for e in load('esquemas.json'))
mes_da_rodada = {}
for r in load('rodadas_cal.json'):
    mes_da_rodada[r['rodada_id']] = int(r['inicio'][5:7])


def clube(cid):
    c = clubes.get(str(cid))
    return c.get('abreviacao') if c else ''


def info(a):
    return {'id': a['atleta_id'], 'nome': a['apelido'], 'pos': POS.get(a['posicao_id'], '?'),
            'clube': clube(a['clube_id']), 'pts': round(a['pontos_num'], 2)}


def r2(x):
    return round(x, 2)

def cor_block(key, tid, cap_rows, luxo_rows, total_time):
    """Tudo o que o time ganhou com atletas do Corinthians (sem bonus de capitao, exceto em 'bonus_capitao')."""
    esc, pts, rodadas_com = 0, 0.0, 0
    por_rodada = []
    jog = {}
    melhor_jogo = None
    for r in RODADAS:
        d = load('%s_%d.json' % (tid, r))
        cor = [a for a in d.get('atletas') or [] if clube(a['clube_id']) == 'COR']
        s = sum(a['pontos_num'] for a in cor)
        por_rodada.append({'rodada': r, 'n': len(cor), 'pts': r2(s)})
        if cor:
            rodadas_com += 1
        esc += len(cor)
        pts += s
        for a in cor:
            j = jog.setdefault(a['atleta_id'], {'nome': a['apelido'], 'pos': POS[a['posicao_id']], 'jogos': 0, 'pts': 0.0})
            j['jogos'] += 1
            j['pts'] += a['pontos_num']
            if melhor_jogo is None or a['pontos_num'] > melhor_jogo['pts']:
                melhor_jogo = {'nome': a['apelido'], 'pos': POS[a['posicao_id']], 'pts': r2(a['pontos_num']), 'rodada': r}
    caps = [c for c in cap_rows if c['clube'] == 'COR']
    luxos = [u for u in luxo_rows if u['clube'] == 'COR']
    jl = sorted(({'nome': j['nome'], 'pos': j['pos'], 'jogos': j['jogos'], 'pts': r2(j['pts']),
                  'media': r2(j['pts'] / j['jogos'])} for j in jog.values()), key=lambda j: -j['pts'])
    return {
        'escalacoes': esc, 'pts': r2(pts), 'media': r2(pts / esc) if esc else 0,
        'share': r2(100 * pts / total_time), 'rodadas_com': rodadas_com,
        'por_rodada': por_rodada, 'jogadores': jl, 'melhor_jogo': melhor_jogo,
        'capitao_vezes': len(caps), 'capitao_pts': r2(sum(c['pts'] for c in caps)),
        'bonus_capitao': r2(sum(c['bonus'] for c in caps)),
        'luxo_usos': len(luxos), 'luxo_ganho': r2(sum(u['ganho'] or 0 for u in luxos)),
    }

out = {'rodadas': RODADAS, 'times': {}, 'meses': []}
escalados = {}  # time -> rodada -> set(atleta_id)

for key, tid, dono, nome in TIMES:
    rod = []
    cap_rows, luxo_rows = [], []
    setor_pts, setor_n = defaultdict(float), defaultdict(int)
    pos_pts, pos_n = defaultdict(float), defaultdict(int)
    jog = {}  # atleta_id -> dict agregado
    esq_cont = defaultdict(int)
    clube_cont = defaultdict(int)
    cap_conf = 0
    cap_acerto = 0
    luxo_designado = 0
    escalados[key] = {}
    for r in RODADAS:
        d = load('%s_%d.json' % (tid, r))
        at = d.get('atletas') or []
        rs = d.get('reservas') or []
        escalados[key][r] = set(a['atleta_id'] for a in at)
        soma = sum(a['pontos_num'] for a in at)
        cap = [a for a in at if a['atleta_id'] == d.get('capitao_id')]
        cap_pts = cap[0]['pontos_num'] if cap else 0.0
        # pontuacao do time = soma dos 12 + 0,5 x capitao (capitao vale 1,5x)
        if abs(soma + 0.5 * cap_pts - d['pontos']) < 0.05:
            cap_conf += 1
        if cap:
            ci = info(cap[0])
            ci.update({'rodada': r, 'bonus': r2(0.5 * cap_pts), 'total': r2(1.5 * cap_pts)})
            linha = [a for a in at if a['posicao_id'] != 6]
            melhor = max(linha, key=lambda a: a['pontos_num'])
            ci['melhor_opcao'] = melhor['apelido']
            ci['melhor_opcao_pts'] = r2(melhor['pontos_num'])
            ci['acertou'] = melhor['pontos_num'] <= cap_pts + 1e-9
            if ci['acertou']:
                cap_acerto += 1
            cap_rows.append(ci)
        lx = d.get('reserva_luxo_id')
        if lx:
            luxo_designado += 1
            ids_tit = dict((a['atleta_id'], a) for a in at)
            ids_res = dict((a['atleta_id'], a) for a in rs)
            if lx in ids_tit:
                L = ids_tit[lx]
                sub = [a for a in rs if a['posicao_id'] == L['posicao_id']]
                li = info(L)
                li['rodada'] = r
                if sub:
                    s = sub[0]
                    li['substituiu'] = s['apelido']
                    li['substituido_pts'] = r2(s['pontos_num'])
                    li['substituido_jogou'] = bool(s['entrou_em_campo'])
                    li['ganho'] = r2(L['pontos_num'] - s['pontos_num'])
                else:
                    li['substituiu'] = None
                    li['substituido_pts'] = None
                    li['substituido_jogou'] = None
                    li['ganho'] = None
                luxo_rows.append(li)
        esq_cont[esquemas.get(d.get('esquema_id'), '?')] += 1
        for a in at:
            p = a['posicao_id']
            setor_pts[SETOR[p]] += a['pontos_num']
            setor_n[SETOR[p]] += 1
            pos_pts[POS[p]] += a['pontos_num']
            pos_n[POS[p]] += 1
            clube_cont[clube(a['clube_id'])] += 1
            j = jog.setdefault(a['atleta_id'], {'id': a['atleta_id'], 'nome': a['apelido'], 'pos': POS[p],
                                                 'clube': clube(a['clube_id']), 'jogos': 0, 'pts': 0.0,
                                                 'max': -99, 'max_rodada': None})
            j['jogos'] += 1
            j['pts'] += a['pontos_num']
            if a['pontos_num'] > j['max']:
                j['max'], j['max_rodada'] = a['pontos_num'], r
        # O "ranking" da API e mensal e por nivel: ranking_id e o nivel do cartoleiro (maior e melhor)
        # e posicao e a colocacao dentro do ranking daquele nivel no mes. Posicoes de niveis diferentes
        # nao se comparam, entao o site usa o nivel.
        rk = d.get('ranking') or {}
        rod.append({'rodada': r, 'pontos': r2(d['pontos']), 'acum': r2(d['pontos_campeonato']),
                    'patrimonio': r2(d['patrimonio']),
                    'nivel': (rk.get('atual') or {}).get('ranking_id'), 'mes_nivel': (rk.get('atual') or {}).get('mes'),
                    'melhor_nivel': rk.get('melhor_ranking_id'),
                    'esquema': esquemas.get(d.get('esquema_id'), '?'), 'cap_pts': r2(cap_pts)})

    for j in jog.values():
        j['pts'] = r2(j['pts'])
        j['max'] = r2(j['max'])
        j['media'] = r2(j['pts'] / j['jogos'])
    jl = list(jog.values())
    pts = [x['pontos'] for x in rod]
    usados = [x for x in luxo_rows if x['ganho'] is not None]
    cap_tot = sum(c['pts'] for c in cap_rows)
    mais_cap = defaultdict(lambda: {'vezes': 0, 'pts': 0.0})
    for c in cap_rows:
        mais_cap[c['nome']]['vezes'] += 1
        mais_cap[c['nome']]['pts'] += c['pts']
    mais_cap = sorted(({'nome': k, 'vezes': v['vezes'], 'pts': r2(v['pts'])} for k, v in mais_cap.items()),
                      key=lambda x: (-x['vezes'], -x['pts']))
    out['times'][key] = {
        'dono': dono, 'nome': nome, 'id': tid, 'rodadas': rod,
        'total': r2(sum(pts)), 'media': r2(sum(pts) / len(pts)),
        'turno1': r2(sum(pts[:19])), 'turno2': r2(sum(pts[19:])),
        'capitao': {
            'rodadas': cap_rows, 'total_bruto': r2(cap_tot), 'bonus_total': r2(cap_tot * 0.5),
            'media': r2(cap_tot / len(cap_rows)), 'acertos': cap_acerto,
            'melhor': max(cap_rows, key=lambda c: c['pts']), 'pior': min(cap_rows, key=lambda c: c['pts']),
            'mais_escolhidos': mais_cap[:5], 'regra_confirmada': cap_conf,
        },
        'luxo': {'designado': luxo_designado, 'acionado': len(luxo_rows), 'usos': luxo_rows,
                 'ganho_total': r2(sum(x['ganho'] for x in usados)),
                 'melhor': max(usados, key=lambda x: x['ganho']) if usados else None},
        'setores': dict((s, {'pts': r2(setor_pts[s]), 'n': setor_n[s],
                             'media': r2(setor_pts[s] / setor_n[s]) if setor_n[s] else 0})
                        for s in ['gol', 'def', 'mei', 'ata', 'tec']),
        'posicoes': dict((p, {'pts': r2(pos_pts[p]), 'n': pos_n[p], 'media': r2(pos_pts[p] / pos_n[p]) if pos_n[p] else 0})
                         for p in ['GOL', 'LAT', 'ZAG', 'MEI', 'ATA', 'TEC']),
        'mais_escalados': sorted(jl, key=lambda j: (-j['jogos'], -j['pts']))[:8],
        'mais_pontos': sorted(jl, key=lambda j: -j['pts'])[:8],
        'melhores_jogos': sorted(jl, key=lambda j: -j['max'])[:5],
        'melhor_por_setor': dict((s, max([j for j in jl if SETOR[[k for k, v in POS.items() if v == j['pos']][0]] == s],
                                          key=lambda j: j['pts'])) for s in ['gol', 'def', 'mei', 'ata', 'tec']),
        'esquemas': sorted(({'nome': k, 'vezes': v} for k, v in esq_cont.items()), key=lambda x: -x['vezes']),
        'clubes': sorted(({'clube': k, 'vezes': v} for k, v in clube_cont.items()), key=lambda x: -x['vezes']),
        'corinthians': cor_block(key, tid, cap_rows, luxo_rows, sum(pts)),
        'mitadas': sum(1 for p in pts if p >= 100),
        'atletas_diferentes': len(jl),
        'melhor_nivel': max([x['melhor_nivel'] or 0 for x in rod] + [x['nivel'] or 0 for x in rod]),
    }

# Comparacoes entre os dois
c, i = out['times']['carlos'], out['times']['igor']
em_comum_rod = [len(escalados['carlos'][r] & escalados['igor'][r]) for r in RODADAS]
out['em_comum'] = {'por_rodada': em_comum_rod, 'media': r2(sum(em_comum_rod) / len(RODADAS)),
                   'max': max(em_comum_rod), 'max_rodada': RODADAS[em_comum_rod.index(max(em_comum_rod))]}
jc = dict((j['id'], j) for j in c['mais_escalados'])
vit = {'carlos': 0, 'igor': 0, 'empate': 0}
for a, b in zip(c['rodadas'], i['rodadas']):
    vit['carlos' if a['pontos'] > b['pontos'] else ('igor' if b['pontos'] > a['pontos'] else 'empate')] += 1
out['vitorias'] = vit
# Maior sequencia de vitorias seguidas
for k in ['carlos', 'igor']:
    best = cur = 0
    for a, b in zip(c['rodadas'], i['rodadas']):
        win = (a['pontos'] > b['pontos']) if k == 'carlos' else (b['pontos'] > a['pontos'])
        cur = cur + 1 if win else 0
        best = max(best, cur)
    out['times'][k]['maior_sequencia'] = best
# Por mes
meses = []
for m in sorted(set(mes_da_rodada[r] for r in RODADAS)):
    rr = [r for r in RODADAS if mes_da_rodada[r] == m]
    pc = sum(c['rodadas'][r - 1]['pontos'] for r in rr)
    pi = sum(i['rodadas'][r - 1]['pontos'] for r in rr)
    meses.append({'mes': MESES[m], 'rodadas': rr, 'carlos': r2(pc), 'igor': r2(pi)})
out['meses'] = meses

with io.open(OUT, 'w', encoding='utf-8') as f:
    f.write(json.dumps(out, ensure_ascii=False))
