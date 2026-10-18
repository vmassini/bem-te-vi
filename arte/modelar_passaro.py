"""Modela os tiranídeos do jogo: bem-te-vi (Pitangus sulphuratus) e bem-te-vi-pirata (Legatus leucophaius).

Uso:  blender -b --factory-startup -P arte/modelar_passaro.py -- <pasta_de_saida> <bemtevi|pirata>
Gera <nome>.glb e as prévias. Os dois compartilham o corpo, as asas e os nós que o jogo anima;
mudam a plumagem, o bico e as bordas das penas.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aves_comum import *   # noqa: F401,F403

args = argumentos()
OUT = pasta_saida(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saida'))
NOME = args[1] if len(args) > 1 else 'bemtevi'

ESPECIES = {
    'bemtevi': dict(
        cores=dict(marrom=0x7a5b36, marrom_esc=0x5a4128, asa=0x6c4c2c, borda=0xc27a37, pena_esc=0x3d2a19,
                   barriga=0xf7c51a, barriga_esc=0xd9a414, sob=0xf3d66c, coroa_escura=0x15110d, mascara=0x15110d,
                   sobrancelha=0xf6f4ee, garganta=0xf6f4ee, coroa=0xffc81a, laranja=0xff9a1a, bico=0x171311,
                   perna=0x2d2926, olho=0x24150b, pupila=0x050403, estria=0x000000, bigode=0x000000),
        bico=dict(L=0.135, W=0.044, Hu=0.027, Ll=0.126, Wl=0.04, Hl=0.017, gancho=0.007),
        estrias=False, bigode=False),
    'pirata': dict(
        cores=dict(marrom=0x5b4a39, marrom_esc=0x45382b, asa=0x54442f, borda=0xc9b48a, pena_esc=0x3a2e22,
                   barriga=0xf0e8c8, barriga_esc=0xd8cea8, sob=0xefe1a2, coroa_escura=0x2a2119, mascara=0x2c231b,
                   sobrancelha=0xede6d4, garganta=0xf3efe5, coroa=0xf0c840, laranja=0xe0a030, bico=0x1f1a16,
                   perna=0x2d2926, olho=0x24150b, pupila=0x050403, estria=0x6a5640, bigode=0x3a2d22),
        bico=dict(L=0.085, W=0.05, Hu=0.022, Ll=0.08, Wl=0.046, Hl=0.015, gancho=0.005),
        estrias=True, bigode=True),
}
E = ESPECIES[NOME]
C = paleta(E['cores'])
C['branco'] = lin(0xf6f4ee)

iniciar()

# ---------- corpo ----------
corpo = blob('corpo', [
    ((0, 0.0, -0.002), (0.098, 0.175, 0.104), (0, 0, 0)),     # tronco
    ((0, -0.075, 0.0), (0.097, 0.11, 0.105), (0, 0, 0)),      # peito
    ((0, -0.03, 0.04), (0.088, 0.14, 0.072), (0, 0, 0)),      # dorso
    ((0, -0.135, 0.065), (0.078, 0.07, 0.082), (0.35, 0, 0)), # pescoço
    ((0, 0.15, 0.028), (0.056, 0.095, 0.05), (-0.15, 0, 0)),  # uropígio
], smooth=(0.8, 30), faces=3000)


def tinta_corpo(p, n):
    costas = sst(0.02, 0.38, n.z) * (1 - sst(0.35, 0.75, -n.y))
    if p.y > 0.13:
        costas = max(costas, sst(-0.1, 0.2, n.z))
    col = mix(C['barriga'], C['marrom'], costas)
    col = mix(col, C['barriga_esc'], 0.35 * sst(0.55, 0.95, abs(n.x)) * (1 - costas))
    if p.y > 0.1 and n.z < 0.0:
        col = mix(col, C['sob'], sst(0.1, 0.2, p.y))
    if E['estrias'] and -0.18 < p.y < 0.08 and costas < 0.5:   # estrias finas e alongadas no peito e flancos
        az = math.atan2(n.x, -n.z)
        tra = sst(0.55, 0.9, math.sin(az * 19 + p.y * 6)) * sst(-0.8, -0.1, math.sin(p.y * 38 + az * 2))
        col = mix(col, C['estria'], 0.8 * tra * sst(0.08, -0.02, p.y) * sst(-0.18, -0.12, p.y))
    return col


paint(corpo, tinta_corpo)

# ---------- cabeça ----------
HC = Vector((0, -0.18, 0.112))         # centro da cabeça
NECK = Vector((0, -0.14, 0.08))        # articulação do pescoço
cabeca = blob('cabeca_malha', [
    ((0, -0.178, 0.114), (0.084, 0.092, 0.08), (0, 0, 0)),    # crânio
    ((0, -0.222, 0.106), (0.06, 0.055, 0.058), (0, 0, 0)),    # testa e loros
    ((0, -0.198, 0.088), (0.066, 0.068, 0.05), (0, 0, 0)),    # bochechas e garganta
    ((0, -0.13, 0.095), (0.07, 0.06, 0.07), (0, 0, 0)),       # nuca
], voxel=0.0028, smooth=(0.8, 20), faces=2600)


def tinta_cabeca(p, n):
    # de baixo para cima: garganta (nuca marrom), [bigode], máscara, sobrancelha, coroa com faixa amarela
    d = p - HC
    r = max(d.length, 1e-6)
    e = math.asin(max(-1.0, min(1.0, d.z / r)))
    fw = -d.y / r
    col = mix(C['garganta'], C['marrom'], sst(-0.3, -0.5, fw))
    if E['bigode']:
        col = mix(col, C['bigode'], sst(-0.72, -0.66, e) * sst(-0.5, -0.56, e) * sst(-0.2, 0.1, fw))
    col = mix(col, C['mascara'], sst(-0.44, -0.36, e))
    col = mix(col, C['sobrancelha'], sst(0.08, 0.15, e))
    col = mix(col, C['coroa_escura'], sst(0.5, 0.57, e))
    faixa = sst(0.015, 0.008, abs(d.x)) * sst(0.76, 0.86, e) * sst(-0.75, -0.6, fw) * sst(0.6, 0.45, fw)
    return mix(col, C['coroa'], faixa)


paint(cabeca, tinta_cabeca)

loc, nor = hit(cabeca, HC, (0, -1, -0.12))
BEAK_BASE = loc + Vector((0, 0.014, -0.004))
B = E['bico']
bsup, binf = Malha(), Malha()
bico(bsup, BEAK_BASE, B['L'], B['W'], B['Hu'], 0.0, B['gancho'], True, C['bico'], n_len=10, n_ring=14)
bico(binf, BEAK_BASE, B['Ll'], B['Wl'], 0.0, B['Hl'], 0.0, False, C['bico'], n_len=10, n_ring=14)

olhos = []
for s in (1, -1):
    a = math.radians(62)
    loc, nor = hit(cabeca, HC, (s * math.sin(a), -math.cos(a), 0.04))
    out = nor.normalized()
    c = loc - out * 0.006
    m = Malha()
    esfera(m, c, (0.0165, 0.0165, 0.0165), lambda n, out=out: C['pupila'] if n.dot(out) > 0.8 else C['olho'], 14, 10)
    esfera(m, c + out * 0.0145 + Vector((0, -0.003, 0.004)), (0.0042, 0.0042, 0.0042), lambda n: C['branco'], 8, 6)
    olhos.append((s, m))

loc, nor = hit(cabeca, HC, (0, 0.12, 1))
CREST = loc - nor * 0.008
crista = Malha()
for k in range(7):
    t = (k - 3) / 3
    root = CREST + Vector((0.004 * t, 0.012 * t, 0))
    pena(crista, frame(root, (0.15 * t, 0.55 + 0.1 * t, 1), (0, -1, 0.5)), 0.055 - 0.008 * abs(t), 0.012,
         C['coroa'], C['laranja'], C['coroa'], curva=0.15, arco=0.2)

# ---------- cauda ----------
TAIL = Vector((0, 0.19, 0.035))
cauda = Malha()
for k, sgn in [(3, 1), (3, -1), (2, 1), (2, -1), (1, 1), (1, -1), (0, 1), (0, -1)]:
    phi = sgn * (0.025 + 0.045 * k)
    root = TAIL + Vector((sgn * 0.008 * k, 0, -0.0022 * (3 - k)))
    pena(cauda, frame(root, (math.sin(phi), math.cos(phi), 0.16), (0, 0, 1)), 0.205 - 0.006 * k, 0.034,
         C['marrom_esc'], C['borda'], C['pena_esc'], curva=-0.05, arco=0.2, lado=sgn)


# ---------- asa fechada (pousado): manto sobre o flanco + primárias sobre o uropígio ----------
def asa_fechada(s):
    mal = Malha()
    nu, nv = 24, 12
    verts, cols, faces = [], [], []
    for i in range(nu + 1):
        u = i / nu
        y = -0.08 + 0.255 * u
        bc = 0.30 + 0.25 * u
        hb = 0.5 * math.sqrt(max(0.0, 1 - ((u - 0.4) / 0.6) ** 2)) + 0.03
        for j in range(nv + 1):
            v = j / nv
            b = bc + (v - 0.5) * 2 * hb
            origin = Vector((0, y, 0.02))
            d = Vector((s * math.cos(b), 0, math.sin(b)))
            loc, nor = hit(corpo, origin, d)
            if loc is None:
                loc, nor = origin + d * 0.1, d
            bulge = math.sin(math.pi * v) * math.sin(math.pi * min(1.0, u * 1.1))
            verts.append(loc + nor * (0.0006 + 0.0045 * bulge))
            c = C['asa']
            if v < 0.5 and u > 0.18:   # franjas das secundárias e terciárias
                c = C['borda'] if (v * 6.5) % 1.0 < 0.28 else C['pena_esc']
            if u > 0.8:
                c = mix(c, C['pena_esc'], 0.5)
            borda = max(sst(0.7, 1.0, v), sst(0.2, 0.0, u))   # bordas de cima e da frente somem no dorso
            cols.append(mix(c, C['marrom'], borda))
    row = nv + 1
    for i in range(nu):
        for j in range(nv):
            a = i * row + j
            faces.append((a, a + row, a + row + 1, a + 1))
    mal.add(verts, faces, cols)
    for k in range(4):
        root = Vector((s * (0.058 - k * 0.003), 0.08 + k * 0.01, 0.058 + k * 0.004))
        pena(mal, frame(root, (-s * 0.17, 1, 0.08), (s, 0, 0.4)), 0.19 - 0.012 * k, 0.025,
             C['pena_esc'], C['borda'], C['coroa_escura'], curva=0.02, arco=0.15, lado=s, nl=9)
    return mal


# ---------- asa aberta (voo): braço com coberteiras e secundárias; mão com primárias ----------
SHOULDER = Vector((0.07, -0.06, 0.07))
ARM = 0.23


def asa_aberta(s):
    braco, mao = Malha(), Malha()
    up = (0, 0, 1)
    esfera(braco, (s * ARM * 0.5, -0.008, 0.004), (ARM * 0.53, 0.032, 0.013),
           lambda n: C['asa'] if n.y < 0.3 else C['marrom_esc'], 14, 8)
    for i in range(10):   # coberteiras pequenas
        pena(braco, frame((s * (0.012 + i * ARM / 10), -0.028, 0.01 - 0.0004 * i), (s * 0.12, 1, 0.02), up), 0.056, 0.026,
             C['asa'], C['marrom'], C['marrom_esc'], curva=0.05, arco=0.3, lado=s, fio=0.75)
    for i in range(9):    # coberteiras grandes
        pena(braco, frame((s * (0.008 + i * ARM / 9), -0.008, 0.006 - 0.0004 * i), (s * 0.18, 1, 0.0), up), 0.088, 0.03,
             C['asa'], C['borda'], C['marrom_esc'], curva=0.04, arco=0.25, lado=s, fio=0.75)
    for i in range(9):    # secundárias
        pena(braco, frame((s * (0.004 + i * ARM / 9), 0.004, -0.0006 * i), (s * (0.05 + 0.03 * i), 1, -0.03), up), 0.15, 0.036,
             C['asa'], C['borda'], C['pena_esc'], curva=0.03, arco=0.2, lado=s, fio=0.7)
    comps = [0.19, 0.205, 0.22, 0.232, 0.242, 0.248, 0.246, 0.235, 0.21]
    for i, L in enumerate(comps):   # primárias, em leque a partir do punho
        th = 1.28 - i * 0.145
        pena(mao, frame((s * (0.004 + 0.006 * i), 0.004 - 0.003 * i, -0.0012 * i), (s * math.cos(th), math.sin(th), -0.02), up),
             L, 0.034, C['pena_esc'], C['borda'], C['coroa_escura'], curva=0.03, arco=0.2, lado=s, fio=0.7)
    for i in range(7):    # coberteiras primárias
        th = 1.05 - i * 0.15
        pena(mao, frame((s * 0.006 * i, -0.006, 0.007), (s * math.cos(th), math.sin(th), 0.0), up), 0.075, 0.028,
             C['asa'], C['borda'], C['marrom_esc'], curva=0.04, arco=0.3, lado=s, fio=0.75)
    return braco, mao


# ---------- pernas ----------
pernas = Malha()
for s in (1, -1):
    tubo(pernas, [(s * 0.04, -0.008, -0.1), (s * 0.041, -0.004, -0.14), (s * 0.042, 0.0, -0.172)],
         [0.0085, 0.0078, 0.007], [C['perna']] * 3)
    F = Vector((s * 0.042, 0.0, -0.177))
    for a, L in [(-0.38, 0.044), (0.0, 0.05), (0.38, 0.042)]:
        d = Vector((math.sin(a) * s, -math.cos(a), -0.12)).normalized()
        tubo(pernas, [F, F + d * L * 0.55 + Vector((0, 0, -0.004)), F + d * L + Vector((0, 0, -0.006))],
             [0.0055, 0.0045, 0.0022], [C['perna'], C['perna'], C['pupila']])
    d = Vector((0, 1, -0.12)).normalized()
    tubo(pernas, [F, F + d * 0.02 + Vector((0, 0, -0.004)), F + d * 0.034 + Vector((0, 0, -0.006))],
         [0.005, 0.0042, 0.0022], [C['perna'], C['perna'], C['pupila']])

# ---------- hierarquia (nós que o jogo anima) ----------
root = empty(NOME, ZERO)
tronco = empty('tronco', ZERO, root)
corpo.parent = tronco
pernas.obj('pernas', M['plumagem']).parent = tronco
for s, lado in ((1, 'D'), (-1, 'E')):
    asa_fechada(s).obj('asa_fechada_' + lado, M['penas']).parent = tronco

e_cab = empty('cabeca', NECK, tronco)
attach(cabeca, e_cab, NECK)
attach(bsup.obj('bico_sup', M['bico']), e_cab, NECK)
e_mand = empty('mandibula', BEAK_BASE, e_cab, NECK)
attach(binf.obj('bico_inf', M['bico']), e_mand, BEAK_BASE)
for s, m in olhos:
    attach(m.obj('olho_' + ('D' if s > 0 else 'E'), M['olho']), e_cab, NECK)
e_crista = empty('crista', CREST, e_cab, NECK)
attach(crista.obj('crista_penas', M['penas']), e_crista, CREST)

for s, lado in ((1, 'D'), (-1, 'E')):
    sh = Vector((s * SHOULDER.x, SHOULDER.y, SHOULDER.z))
    wr = sh + Vector((s * ARM, 0.02, 0))
    e_asa = empty('asa_' + lado, sh, tronco)
    e_mao = empty('mao_' + lado, wr, e_asa, sh)
    braco, mao = asa_aberta(s)
    braco.obj('asa_%s_braco' % lado, M['penas']).parent = e_asa
    mao.obj('asa_%s_mao' % lado, M['penas']).parent = e_mao   # vértices já estão no referencial do punho

e_cauda = empty('cauda', TAIL, tronco)
attach(cauda.obj('cauda_penas', M['penas']), e_cauda, TAIL)

exportar_glb(os.path.join(OUT, NOME + '.glb'))

# ---------- prévias ----------
OB = bpy.data.objects


def pose(pousado=True, bater=0.0, canto=0.0, crista=0.1, olhar=0.0):
    ereto = -0.38 if pousado else 0.0
    OB['tronco'].rotation_euler = (ereto, 0, 0)
    OB['pernas'].rotation_euler = (-ereto, 0, 0)
    OB['pernas'].hide_render = not pousado
    OB['galho'].hide_render = not pousado
    OB['cabeca'].rotation_euler = (-ereto - 0.3 * canto + (0.12 if not pousado else 0), 0, olhar)
    OB['mandibula'].rotation_euler = (0.45 * canto, 0, 0)
    OB['crista'].scale = (1, 1, max(crista, 0.02))
    for lado, s in (('D', 1), ('E', -1)):
        OB['asa_fechada_' + lado].hide_render = not pousado
        OB['asa_%s_braco' % lado].hide_render = pousado
        OB['asa_%s_mao' % lado].hide_render = pousado
        OB['asa_' + lado].rotation_euler = (0, -s * bater, s * 0.1)
        OB['mao_' + lado].rotation_euler = (0, -s * bater * 0.45, 0)
    OB['cauda'].scale = (1.0 if pousado else 1.45, 1, 1)
    OB['cauda'].rotation_euler = (0.18 if pousado else -0.05, 0, 0)


previas(OUT, NOME, [
    ('perfil', dict(pousado=True, olhar=0.25), (1.2, -0.05, 0.1), (0, 0.0, -0.01)),
    ('frente', dict(pousado=True, olhar=-0.35), (0.75, -0.95, 0.22), (0, -0.04, 0.0)),
    ('costas', dict(pousado=True, olhar=0.6), (-0.75, 0.95, 0.45), (0, 0.02, 0.0)),
    ('cantando', dict(pousado=True, canto=1.0, crista=1.0, olhar=-0.2), (0.42, -0.62, 0.32), (0, -0.16, 0.13)),
    ('voo_de_cima', dict(pousado=False, bater=0.05, crista=0.1), (0.0, 0.75, 2.5), (0, 0.06, 0.0)),
    ('voo_asas_altas', dict(pousado=False, bater=0.55, crista=0.1), (0.7, -0.95, 0.8), (0, 0.04, 0.03)),
    ('voo_asas_baixas', dict(pousado=False, bater=-0.5, crista=0.1), (-1.0, -0.55, -0.3), (0, 0.04, 0.0)),
    ('voo_de_lado', dict(pousado=False, bater=0.2, crista=0.1), (1.4, 0.15, 0.35), (0, 0.04, 0.03)),
], pose)
