# -*- coding: utf-8 -*-
# Monta o site inteiro: baixa os dados, roda as analises, gera index.html e og.png.
# Uso: python build/montar.py [--sem-baixar <pasta_dados>] [--forcar]
# Sai sem mexer em nada quando os dados e o codigo nao mudaram desde a ultima montagem.
#
# Temporadas: a API do Cartola so tem a temporada atual. Cada temporada fica guardada em
# build/arquivo/<ano>.json. A pagina principal mostra a temporada atual (ou, na pre-temporada,
# a ultima completa) e as outras ganham uma pagina propria em temporadas/<ano>/.
import glob, hashlib, json, os, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ARQUIVO = os.path.join(AQUI, 'arquivo')
BRASILIA = timezone(timedelta(hours=-3))
MESES = ['', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
SITE = 'https://igorcossermelli.github.io/cartola-igor-x-carlos/'
TOTAL = int(os.environ.get('TOTAL_RODADAS', '38'))  # so muda em teste


def rodar(script, *args, env=None):
    saida = subprocess.run([sys.executable, os.path.join(AQUI, script)] + list(args), check=True,
                           capture_output=True, text=True, encoding='utf-8', env=env)
    return saida.stdout.strip()


def fmt(v, d=1):
    s = '{:,.{}f}'.format(v, d)
    return s.replace(',', 'X').replace('.', ',').replace('X', '.')


def quesitos(o):
    """Lista de quesitos do placar geral. O site e a imagem de previa usam esta mesma lista."""
    C, I = o['times']['carlos'], o['times']['igor']
    XC, XI = o['extras']['times']['carlos'], o['extras']['times']['igor']
    ult = lambda t: t['rodadas'][-1]
    maxr = lambda t: max(r['pontos'] for r in t['rodadas'])
    n = len(C['rodadas'])
    # (rotulo, nome curto usado no resumo, Carlos, Igor, casas decimais; -1 = menor e melhor)
    lista = [
        ('Pontos no campeonato', 'total de pontos', C['total'], I['total'], 1),
        ('Rodadas vencidas', 'rodadas vencidas', o['vitorias']['carlos'], o['vitorias']['igor'], 0),
        ('Pontos no 1º turno (rodadas 1 a %d)' % min(19, n), '1º turno', C['turno1'], I['turno1'], 1),
    ]
    if n >= 20:  # o 2º turno so existe a partir da rodada 20
        lista.append(('Pontos no 2º turno (rodadas 20 a %d)' % n, '2º turno', C['turno2'], I['turno2'], 1))
    lista += [
        ('Meses vencidos', 'meses vencidos', sum(1 for m in o['meses'] if m['carlos'] > m['igor']), sum(1 for m in o['meses'] if m['igor'] > m['carlos']), 0),
        ('Maior sequência de rodadas vencidas', 'maior sequência de vitórias', C['maior_sequencia'], I['maior_sequencia'], 0),
        ('Maior pontuação numa rodada', 'maior rodada', maxr(C), maxr(I), 1),
        ('Pontos dos capitães (sem o bônus)', 'capitães', C['capitao']['total_bruto'], I['capitao']['total_bruto'], 1),
        ('Ganho com o reserva de luxo', 'reserva de luxo', C['luxo']['ganho_total'], I['luxo']['ganho_total'], 1),
    ]
    for k, nome in [('gol', 'goleiro'), ('def', 'defesa'), ('mei', 'meio-campo'), ('ata', 'ataque'), ('tec', 'técnico')]:
        lista.append(('Média do setor: ' + nome, nome, C['setores'][k]['media'], I['setores'][k]['media'], 2))
    lista += [
        ('Gols dos escalados', 'gols', XC['scouts']['gols'], XI['scouts']['gols'], 0),
        ('Assistências dos escalados', 'assistências', XC['scouts']['assist'], XI['scouts']['assist'], 0),
        ('Pontos por cartoleta gasta', 'pontos por cartoleta', round(C['total'] / XC['custo']['total'], 4), round(I['total'] / XI['custo']['total'], 4), 3),
        ('Aproveitamento do time ideal (%)', 'time ideal', XC['ideal']['media'], XI['ideal']['media'], 1),
        ('Pontos de jogadores do Corinthians', 'pontos do Corinthians', C['corinthians']['pts'], I['corinthians']['pts'], 1),
        ('Patrimônio final (cartoletas)', 'patrimônio', ult(C)['patrimonio'], ult(I)['patrimonio'], 2),
        ('Posição no ranking geral (menor é melhor)', 'ranking geral', ult(C)['ranking'], ult(I)['ranking'], -1),
    ]
    out = []
    for lbl, curto, a, b, d in lista:
        menor = d == -1
        out.append({'lbl': lbl, 'curto': curto, 'a': a, 'b': b, 'd': d,
                    'win': ('c' if (a < b if menor else a > b) else 'i' if (b < a if menor else b > a) else '')})
    return out


# ---------- Imagem de previa (1200 x 630) ----------
def escudo(draw, x, y, w, fundo, cruz, borda):
    h = w * 1.2
    pts = [(x, y), (x + w, y), (x + w, y + h * 0.52)]
    for k in range(1, 21):  # curva da parte de baixo do escudo
        t = k / 20.0
        if t <= 0.5:
            u = t * 2
            px = (1 - u) ** 2 * (x + w) + 2 * (1 - u) * u * (x + w) + u ** 2 * (x + w / 2)
            py = (1 - u) ** 2 * (y + h * 0.52) + 2 * (1 - u) * u * (y + h * 0.82) + u ** 2 * (y + h * 0.97)
        else:
            u = (t - 0.5) * 2
            px = (1 - u) ** 2 * (x + w / 2) + 2 * (1 - u) * u * x + u ** 2 * x
            py = (1 - u) ** 2 * (y + h * 0.97) + 2 * (1 - u) * u * (y + h * 0.82) + u ** 2 * (y + h * 0.52)
        pts.append((px, py))
    draw.polygon(pts, fill=fundo)
    from PIL import Image, ImageDraw
    mascara = Image.new('L', draw.im.size, 0)
    ImageDraw.Draw(mascara).polygon(pts, fill=255)
    cruz_img = Image.new('RGBA', draw.im.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(cruz_img)
    cd.rectangle([x + w * 0.41, y, x + w * 0.58, y + h], fill=cruz)
    cd.rectangle([x, y + h * 0.27, x + w, y + h * 0.39], fill=cruz)
    return pts, mascara, cruz_img


def imagem_previa(o, q, destino):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    img = Image.new('RGB', (W, H), '#0d1424')
    d = ImageDraw.Draw(img)
    # metades nas cores dos times
    for yy in range(H - 90):
        f = yy / (H - 90)
        d.line([(0, yy), (W // 2, yy)], fill=(int(47 - 18 * f), int(98 - 29 * f), int(232 - 36 * f)))
        d.line([(W // 2, yy), (W, yy)], fill=(int(27 - 20 * f),) * 3)
    sobre = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sobre)
    sd.rectangle([230, 0, 320, H - 90], fill=(63, 180, 255, 55))
    sd.rectangle([0, 150, W // 2, 215], fill=(63, 180, 255, 55))
    sd.rectangle([W // 2 + 290, 0, W // 2 + 380, H - 90], fill=(242, 194, 48, 45))
    sd.rectangle([W // 2, 150, W, 215], fill=(242, 194, 48, 45))
    img.paste(sobre, (0, 0), sobre)
    d = ImageDraw.Draw(img)
    d.rectangle([W // 2 - 5, 0, W // 2 + 5, H - 90], fill='#d9302a')
    fonte = lambda n, peso='ExtraBold': ImageFont.truetype(os.path.join(AQUI, 'fontes', 'BarlowCondensed-%s.ttf' % peso), n)
    # escudos
    for (x, fundo, cruz) in [(60, '#2f62e8', '#3fb4ff'), (W - 60 - 130, '#111111', '#f2c230')]:
        pts, mascara, cruz_img = escudo(d, x, 40, 130, fundo, cruz, '#d9302a')
        img.paste(cruz_img, (0, 0), Image.composite(cruz_img, Image.new('RGBA', (W, H)), mascara))
        d = ImageDraw.Draw(img)
        d.line(pts + [pts[0]], fill='#d9302a', width=8, joint='curve')
    d.text((210, 70), 'RB PAPAI', font=fonte(66), fill='white')
    d.text((212, 140), 'Carlos', font=fonte(32, 'SemiBold'), fill=(220, 230, 255))
    d.text((W - 210, 70), 'IGOR PRO F.C', font=fonte(66), fill='white', anchor='ra')
    d.text((W - 212, 140), 'Igor', font=fonte(32, 'SemiBold'), fill=(242, 225, 170), anchor='ra')
    # placar
    qc = sum(1 for x in q if x['win'] == 'c')
    qi = sum(1 for x in q if x['win'] == 'i')
    d.rounded_rectangle([W // 2 - 210, 250, W // 2 + 210, 470], radius=22, fill='#0d1424', outline='#d9302a', width=6)
    d.text((W // 2 - 40, 405), str(qc), font=fonte(150), fill='#8fb3ff', anchor='rs')
    d.text((W // 2, 360), '×', font=fonte(60, 'SemiBold'), fill='#9aa6bd', anchor='mm')
    d.text((W // 2 + 40, 405), str(qi), font=fonte(150), fill='#f2c230', anchor='ls')
    d.text((W // 2, 442), 'QUESITOS VENCIDOS', font=fonte(30, 'SemiBold'), fill='#9aa6bd', anchor='mm')
    # faixa de baixo
    C, I = o['times']['carlos'], o['times']['igor']
    n = len(C['rodadas'])
    d.rectangle([0, H - 90, W, H], fill='#0d1424')
    d.rectangle([0, H - 90, W, H - 84], fill='#d9302a')
    texto = 'CARTOLA %s  ·  RODADAS 1 A %d  ·  PONTOS %s × %s' % (o['temporada'], n, fmt(C['total']), fmt(I['total']))
    d.text((W // 2, H - 42), texto, font=fonte(38, 'SemiBold'), fill='#f2f5fa', anchor='mm')
    img.save(destino, 'PNG', optimize=True)


def analisar(pasta, ultima, temporada):
    env = dict(os.environ, ULTIMA=str(ultima), TOTAL_RODADAS=str(TOTAL))
    saida = os.path.join(pasta, 'site_data.json')
    rodar('analise.py', pasta, saida, env=env)
    rodar('extras.py', pasta, saida, env=env)
    with open(saida, encoding='utf-8') as f:
        o = json.load(f)
    o['quesitos'] = quesitos(o)
    o['temporada'] = temporada
    o['ultima'] = ultima
    return o


def ler_arquivo():
    """Temporadas guardadas: {ano: dados}."""
    out = {}
    for caminho in glob.glob(os.path.join(ARQUIVO, '*.json')):
        with open(caminho, encoding='utf-8') as f:
            o = json.load(f)
        out[int(o['temporada'])] = o
    return out


def agora_texto():
    agora = datetime.now(BRASILIA)
    return '%d de %s de %d, %02dh%02d' % (agora.day, MESES[agora.month], agora.year, agora.hour, agora.minute)


def renderizar(o, pasta_saida, base, links, atual, aviso, hash_curto):
    """Gera index.html e og.png de uma temporada. base: caminho ate a raiz do site a partir da pagina."""
    ultima = o['ultima']
    o = dict(o)
    o['meta'] = {'ultima': ultima, 'total': TOTAL, 'restantes': (TOTAL - ultima) if atual else 0,
                 'atual': atual, 'temporada': o['temporada'], 'aviso': aviso,
                 'temporadas': sorted(links, reverse=True), 'links': {str(k): v for k, v in links.items()},
                 'atualizado': o.get('atualizado') or agora_texto()}
    qc = sum(1 for x in o['quesitos'] if x['win'] == 'c')
    qi = sum(1 for x in o['quesitos'] if x['win'] == 'i')
    url = SITE + ('' if base == '' else 'temporadas/%s/' % o['temporada'])
    with open(os.path.join(AQUI, 'template.html'), encoding='utf-8') as f:
        t = f.read()
    dados = json.dumps(o, ensure_ascii=False).replace('</', '<\\/')
    t = (t.replace('__DATA__', dados)
          .replace('__OG_IMG__', url + 'og.png?v=%s-%d-%s' % (o['temporada'], ultima, hash_curto))
          .replace('__OG_DESC__', 'Placar de quesitos: Carlos %d × %d Igor. Rodadas 1 a %d do Cartola %s.' % (qc, qi, ultima, o['temporada']))
          .replace('__TEMPORADA__', str(o['temporada']))
          .replace('__SITE__', url))
    os.makedirs(pasta_saida, exist_ok=True)
    with open(os.path.join(pasta_saida, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(t)
    imagem_previa(o, o['quesitos'], os.path.join(pasta_saida, 'og.png'))
    return qc, qi


def main():
    args = sys.argv[1:]
    forcar = '--forcar' in args
    if '--sem-baixar' in args:
        pasta = args[args.index('--sem-baixar') + 1]
    else:
        pasta = tempfile.mkdtemp(prefix='cartola-')
        rodar('baixar.py', pasta)
    with open(os.path.join(pasta, 'status.json'), encoding='utf-8') as f:
        st = json.load(f)
    temporada = int(st.get('temporada') or datetime.now(BRASILIA).year)
    ultima = TOTAL if st.get('game_over') else st['rodada_atual'] - 1
    ultima = int(os.environ.get('ULTIMA_TESTE', ultima))  # so muda em teste

    arquivo = ler_arquivo()
    atual = analisar(pasta, ultima, temporada) if ultima >= 1 else None
    if atual is None and not arquivo:
        print('Nenhuma rodada pontuada e nenhuma temporada guardada. Nada a fazer.')
        return
    principal = atual or arquivo[max(arquivo)]
    em_andamento = atual is not None and ultima < TOTAL
    if atual is None:
        aviso = 'A temporada %d ainda não começou. Enquanto isso, o site mostra a temporada %d completa.' % (temporada, principal['temporada'])
    else:
        aviso = ''

    # O hash junta os dados (sem data de atualizacao), as temporadas guardadas e o codigo.
    h = hashlib.sha256()
    h.update(json.dumps({k: v for k, v in principal.items() if k != 'atualizado'}, sort_keys=True, ensure_ascii=False).encode('utf-8'))
    h.update(json.dumps(sorted(k for k in arquivo if k != principal['temporada'])).encode('utf-8'))
    h.update(str(em_andamento).encode('utf-8'))
    for nome in ['template.html', 'montar.py', 'analise.py', 'extras.py']:
        with open(os.path.join(AQUI, nome), 'rb') as f:
            h.update(f.read())
    hash_novo = h.hexdigest()
    arq_hash = os.path.join(AQUI, 'ultimo_hash.txt')
    hash_antigo = open(arq_hash).read().strip() if os.path.exists(arq_hash) else ''
    if hash_novo == hash_antigo and not forcar:
        print('Sem mudanças (temporada %d, rodada %d).' % (principal['temporada'], principal['ultima']))
        return

    # Guarda a temporada atual no arquivo, com a data desta atualizacao.
    if atual is not None:
        atual['atualizado'] = agora_texto()
        os.makedirs(ARQUIVO, exist_ok=True)
        with open(os.path.join(ARQUIVO, '%d.json' % temporada), 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(atual, ensure_ascii=False, sort_keys=True))
        arquivo[temporada] = atual

    anos = sorted(set(arquivo) | {principal['temporada']}, reverse=True)
    # Pagina principal: temporada atual (ou a ultima guardada, na pre-temporada)
    links_raiz = {a: ('./' if a == principal['temporada'] else 'temporadas/%d/' % a) for a in anos}
    qc, qi = renderizar(principal, RAIZ, '', links_raiz, em_andamento, aviso, hash_novo[:8])
    # Paginas das outras temporadas
    for a in anos:
        if a == principal['temporada']:
            continue
        links = {b: ('../../' if b == principal['temporada'] else '../%d/' % b) for b in anos}
        renderizar(arquivo[a], os.path.join(RAIZ, 'temporadas', str(a)), '../../', links, False, '', hash_novo[:8])

    with open(arq_hash, 'w') as f:
        f.write(hash_novo + '\n')
    with open(os.path.join(AQUI, 'ultima.txt'), 'w') as f:
        f.write('%d, rodada %d\n' % (principal['temporada'], principal['ultima']))
    print('Site montado: temporada %d até a rodada %d (Carlos %d × %d Igor).' % (principal['temporada'], principal['ultima'], qc, qi))


if __name__ == '__main__':
    main()
