# -*- coding: utf-8 -*-
# Monta o site inteiro: baixa os dados, roda as analises, gera index.html e og.png.
# Uso: python build/montar.py [--sem-baixar <pasta_dados>] [--forcar]
# Sai sem mexer em nada quando os dados e o codigo nao mudaram desde a ultima montagem.
import hashlib, json, os, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BRASILIA = timezone(timedelta(hours=-3))
MESES = ['', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
SITE = 'https://igorcossermelli.github.io/cartola-igor-x-carlos/'


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
    lista = [
        ('Pontos no campeonato', C['total'], I['total'], 1),
        ('Rodadas vencidas', o['vitorias']['carlos'], o['vitorias']['igor'], 0),
        ('Pontos no 1º turno (rodadas 1 a 19)', C['turno1'], I['turno1'], 1),
        ('Pontos no 2º turno (rodadas 20 a %d)' % n, C['turno2'], I['turno2'], 1),
        ('Meses vencidos', sum(1 for m in o['meses'] if m['carlos'] > m['igor']), sum(1 for m in o['meses'] if m['igor'] > m['carlos']), 0),
        ('Maior sequência de rodadas vencidas', C['maior_sequencia'], I['maior_sequencia'], 0),
        ('Maior pontuação numa rodada', maxr(C), maxr(I), 1),
        ('Pontos dos capitães (sem o bônus)', C['capitao']['total_bruto'], I['capitao']['total_bruto'], 1),
        ('Ganho com o reserva de luxo', C['luxo']['ganho_total'], I['luxo']['ganho_total'], 1),
    ]
    for k, nome in [('gol', 'goleiro'), ('def', 'defesa'), ('mei', 'meio-campo'), ('ata', 'ataque'), ('tec', 'técnico')]:
        lista.append(('Média do setor: ' + nome, C['setores'][k]['media'], I['setores'][k]['media'], 2))
    lista += [
        ('Gols dos escalados', XC['scouts']['gols'], XI['scouts']['gols'], 0),
        ('Assistências dos escalados', XC['scouts']['assist'], XI['scouts']['assist'], 0),
        ('Pontos por cartoleta gasta', round(C['total'] / XC['custo']['total'], 4), round(I['total'] / XI['custo']['total'], 4), 3),
        ('Aproveitamento do time ideal (%)', XC['ideal']['media'], XI['ideal']['media'], 1),
        ('Pontos de jogadores do Corinthians', C['corinthians']['pts'], I['corinthians']['pts'], 1),
        ('Patrimônio final (cartoletas)', ult(C)['patrimonio'], ult(I)['patrimonio'], 2),
        ('Posição no ranking geral (menor é melhor)', ult(C)['ranking'], ult(I)['ranking'], -1),
    ]
    out = []
    for lbl, a, b, d in lista:
        menor = d == -1
        out.append({'lbl': lbl, 'a': a, 'b': b, 'd': d,
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
    texto = 'CARTOLA 2026  ·  RODADAS 1 A %d  ·  PONTOS %s × %s' % (n, fmt(C['total']), fmt(I['total']))
    d.text((W // 2, H - 42), texto, font=fonte(38, 'SemiBold'), fill='#f2f5fa', anchor='mm')
    img.save(destino, 'PNG', optimize=True)


def main():
    args = sys.argv[1:]
    forcar = '--forcar' in args
    if '--sem-baixar' in args:
        pasta = args[args.index('--sem-baixar') + 1]
        with open(os.path.join(pasta, 'status.json'), encoding='utf-8') as f:
            st = json.load(f)
        ultima = 38 if st.get('game_over') else st['rodada_atual'] - 1
    else:
        pasta = tempfile.mkdtemp(prefix='cartola-')
        ultima = int(rodar('baixar.py', pasta))
    env = dict(os.environ, ULTIMA=str(ultima))
    saida = os.path.join(pasta, 'site_data.json')
    rodar('analise.py', pasta, saida, env=env)
    rodar('extras.py', pasta, saida, env=env)
    with open(saida, encoding='utf-8') as f:
        o = json.load(f)
    o['quesitos'] = quesitos(o)

    # O hash junta dados e codigo: se nada mudou, nao ha o que publicar.
    h = hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode('utf-8'))
    for nome in ['template.html', 'montar.py', 'analise.py', 'extras.py']:
        with open(os.path.join(AQUI, nome), 'rb') as f:
            h.update(f.read())
    hash_novo = h.hexdigest()
    arq_hash = os.path.join(AQUI, 'ultimo_hash.txt')
    hash_antigo = open(arq_hash).read().strip() if os.path.exists(arq_hash) else ''
    if hash_novo == hash_antigo and not forcar:
        print('Sem mudanças (rodada %d).' % ultima)
        return

    agora = datetime.now(BRASILIA)
    o['meta'] = {'ultima': ultima, 'restantes': 38 - ultima,
                 'atualizado': '%d de %s de %d, %02dh%02d' % (agora.day, MESES[agora.month], agora.year, agora.hour, agora.minute)}
    qc = sum(1 for x in o['quesitos'] if x['win'] == 'c')
    qi = sum(1 for x in o['quesitos'] if x['win'] == 'i')
    with open(os.path.join(AQUI, 'template.html'), encoding='utf-8') as f:
        t = f.read()
    dados = json.dumps(o, ensure_ascii=False).replace('</', '<\\/')
    t = (t.replace('__DATA__', dados)
          .replace('__OG_IMG__', SITE + 'og.png?v=%d-%s' % (ultima, hash_novo[:8]))
          .replace('__OG_DESC__', 'Placar de quesitos: Carlos %d × %d Igor. Rodadas 1 a %d do Cartola 2026.' % (qc, qi, ultima))
          .replace('__SITE__', SITE))
    with open(os.path.join(RAIZ, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(t)
    imagem_previa(o, o['quesitos'], os.path.join(RAIZ, 'og.png'))
    with open(arq_hash, 'w') as f:
        f.write(hash_novo + '\n')
    with open(os.path.join(AQUI, 'ultima.txt'), 'w') as f:
        f.write(str(ultima) + '\n')
    print('Site montado até a rodada %d (Carlos %d × %d Igor).' % (ultima, qc, qi))


if __name__ == '__main__':
    main()
