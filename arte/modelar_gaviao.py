"""Modela o gavião-carijó (Rupornis magnirostris), o gavião mais comum nas cidades brasileiras.

Uso:  blender -b --factory-startup -P arte/modelar_gaviao.py -- <pasta_de_saida>
Nós que o jogo anima: tronco, cabeca, asa_D/asa_E (+ mao_D/mao_E), cauda e garras (aparecem no mergulho).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aves_comum import *   # noqa: F401,F403

OUT = pasta_saida(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saida'))
C = paleta(dict(cinza=0x6d665e, cinza_esc=0x4f4943, peito=0x857a6e, barra=0xb8774a, branco=0xefe6d6, garganta=0xa59b8f,
                iris=0xe8c11e, pupila=0x0a0a0a, cera=0xf2c12e, bico=0x2b2622, perna=0xf0c22a, garra=0x151515,
                ferrugem=0xb46a3a, pena=0x5a524a, faixa=0x2f2a26, cauda=0x8d8378, ponta=0xd9d2c6, brilho=0xffffff))
iniciar()

# ---------- corpo: dorso cinza-pardo, peito liso, ventre e calças barrados ----------
corpo = blob('corpo', [
    ((0, 0.0, 0.0), (0.11, 0.19, 0.12), (0, 0, 0)),
    ((0, -0.09, 0.01), (0.105, 0.12, 0.115), (0, 0, 0)),
    ((0, -0.165, 0.075), (0.075, 0.07, 0.08), (0.35, 0, 0)),
    ((0, 0.17, 0.03), (0.06, 0.1, 0.05), (-0.1, 0, 0)),
    ((0.05, 0.03, -0.095), (0.042, 0.055, 0.045), (0, 0, 0)),    # "calças"
    ((-0.05, 0.03, -0.095), (0.042, 0.055, 0.045), (0, 0, 0)),
], voxel=0.0042, smooth=(0.8, 26), faces=3200)


def tinta_corpo(p, n):
    costas = sst(0.05, 0.4, n.z) * (1 - sst(0.35, 0.75, -n.y))
    barrado = mix(C['branco'], C['barra'], sst(-0.2, 0.3, math.sin(p.z * 150 + p.y * 10)))
    baixo = mix(barrado, C['peito'], sst(-0.03, -0.1, p.y) * sst(-0.03, 0.04, p.z))
    col = mix(baixo, C['cinza'], costas)
    if p.y > 0.14 and n.z < 0:
        col = mix(col, C['branco'], sst(0.14, 0.22, p.y))
    return col


paint(corpo, tinta_corpo)

# ---------- cabeça com sobrancelha saliente ----------
HC = Vector((0, -0.2, 0.12))
NECK = Vector((0, -0.16, 0.09))
cabeca = blob('cabeca_malha', [
    ((0, -0.198, 0.122), (0.085, 0.094, 0.08), (0, 0, 0)),
    ((0, -0.236, 0.142), (0.066, 0.045, 0.03), (0, 0, 0)),     # arco supraorbital
    ((0, -0.22, 0.095), (0.07, 0.072, 0.058), (0, 0, 0)),
    ((0, -0.145, 0.11), (0.07, 0.06, 0.07), (0, 0, 0)),
], voxel=0.003, smooth=(0.8, 18), faces=2400)


def tinta_cabeca(p, n):
    d = p - HC
    r = max(d.length, 1e-6)
    e = math.asin(max(-1.0, min(1.0, d.z / r)))
    fw = -d.y / r
    col = C['cinza']
    gar = sst(-0.25, -0.4, e) * sst(-0.1, 0.2, fw)
    col = mix(col, mix(C['garganta'], C['cinza_esc'], sst(0.2, 0.7, math.sin(d.x * 220))), gar)
    return col


paint(cabeca, tinta_cabeca)
olhos = Malha()
for s in (1, -1):
    ed = Vector((s * math.sin(math.radians(52)), -math.cos(math.radians(52)), 0.06))
    loc, nor = hit(cabeca, HC, ed)
    olho(olhos, loc - nor * 0.007, nor.normalized(), 0.018, C['iris'], C['pupila'], C['brilho'], pupila=0.88)

loc, nor = hit(cabeca, HC, (0, -1, -0.1))
BASE = loc + Vector((0, 0.014, 0.0))
bicom = Malha()
bico(bicom, BASE, 0.075, 0.044, 0.044, 0.0, 0.034, True, None, cor_fn=lambda t, sz: C['cera'] if t < 0.28 else C['bico'])
bico(bicom, BASE, 0.055, 0.04, 0.0, 0.02, 0.0, False, None, cor_fn=lambda t, sz: C['cera'] if t < 0.2 else C['bico'])

# ---------- asas largas: primárias ferrugem com pontas escuras ("dedos"), secundárias barradas ----------
SHOULDER = Vector((0.09, -0.07, 0.08))
ARM = 0.34


def asa(s):
    braco, mao = Malha(), Malha()
    up = (0, 0, 1)
    esfera(braco, (s * ARM * 0.5, -0.01, 0.005), (ARM * 0.53, 0.04, 0.016), lambda n: C['cinza'], 14, 8)
    for i in range(11):
        pena(braco, frame((s * (0.012 + i * ARM / 11), -0.034, 0.012 - 0.0004 * i), (s * 0.12, 1, 0.02), up), 0.085, 0.036,
             C['cinza'], C['cinza_esc'], C['cinza_esc'], curva=0.05, arco=0.3, lado=s, fio=0.8)
    for i in range(11):
        pena(braco, frame((s * (0.004 + i * ARM / 11), 0.004, -0.0006 * i), (s * (0.03 + 0.022 * i), 1, -0.03), up), 0.22, 0.05,
             C['pena'], C['cinza_esc'], C['faixa'], curva=0.03, arco=0.2, lado=s, fio=0.8, faixas=3, cor_faixa=C['faixa'])
    for i, Lp in enumerate([0.26, 0.29, 0.31, 0.32, 0.31, 0.28]):
        th = 1.2 - i * 0.22
        pena(mao, frame((s * (0.004 + 0.008 * i), 0.004 - 0.004 * i, -0.0014 * i), (s * math.cos(th), math.sin(th), -0.03), up),
             Lp, 0.048, C['ferrugem'], C['cinza_esc'], C['faixa'], curva=0.05, arco=0.2, lado=s, fio=0.8, faixas=2.5, cor_faixa=C['faixa'])
    return braco, mao


TAIL = Vector((0, 0.24, 0.04))
cauda = Malha()
for k, sgn in [(4, 1), (4, -1), (3, 1), (3, -1), (2, 1), (2, -1), (1, 1), (1, -1), (0, 1), (0, -1)]:
    phi = sgn * (0.015 + 0.035 * k)
    pena(cauda, frame(TAIL + Vector((sgn * 0.01 * k, 0, -0.002 * (4 - k))), (math.sin(phi), math.cos(phi), 0.05), (0, 0, 1)),
         0.27 - 0.006 * k, 0.05, C['cauda'], C['cinza'], C['ponta'], curva=-0.02, arco=0.2, lado=sgn, fio=0.8,
         faixas=2.2, cor_faixa=C['faixa'])

# ---------- garras: pernas amarelas e unhas pretas, esticadas para a frente ----------
garras = Malha()
for s in (1, -1):
    joelho = Vector((s * 0.05, 0.02, -0.12))
    pe = Vector((s * 0.05, -0.07, -0.2))
    tubo(garras, [joelho, joelho.lerp(pe, 0.5), pe], [0.012, 0.011, 0.01], [C['perna']] * 3)
    for a in (-0.45, 0.0, 0.45):
        d = Vector((math.sin(a) * s * 0.8, -math.cos(a), -0.35)).normalized()
        tubo(garras, [pe, pe + d * 0.035, pe + d * 0.05 + Vector((0, 0, -0.012))], [0.008, 0.006, 0.002],
             [C['perna'], C['garra'], C['garra']])
    d = Vector((0, 1, -0.4)).normalized()
    tubo(garras, [pe, pe + d * 0.03, pe + d * 0.045 + Vector((0, 0, -0.01))], [0.008, 0.006, 0.002], [C['perna'], C['garra'], C['garra']])

# ---------- hierarquia ----------
root = empty('gaviao', ZERO)
tronco = empty('tronco', ZERO, root)
corpo.parent = tronco
garras.obj('garras', M['plumagem']).parent = tronco
e_cab = empty('cabeca', NECK, tronco)
attach(cabeca, e_cab, NECK)
attach(bicom.obj('bico', M['bico']), e_cab, NECK)
attach(olhos.obj('olhos', M['olho']), e_cab, NECK)
for s, lado in ((1, 'D'), (-1, 'E')):
    sh = Vector((s * SHOULDER.x, SHOULDER.y, SHOULDER.z))
    e_asa = empty('asa_' + lado, sh, tronco)
    e_mao = empty('mao_' + lado, sh + Vector((s * ARM, 0.02, 0)), e_asa, sh)
    braco, mao = asa(s)
    braco.obj('asa_%s_braco' % lado, M['penas']).parent = e_asa
    mao.obj('asa_%s_mao' % lado, M['penas']).parent = e_mao
e_cauda = empty('cauda', TAIL, tronco)
attach(cauda.obj('cauda_penas', M['penas']), e_cauda, TAIL)

exportar_glb(os.path.join(OUT, 'gaviao.glb'))

OB = bpy.data.objects


def pose(bater=0.0, mergulho=False):
    OB['garras'].hide_render = not mergulho
    OB['tronco'].rotation_euler = (0.5 if mergulho else 0.0, 0, 0)
    for lado, s in (('D', 1), ('E', -1)):
        OB['asa_' + lado].rotation_euler = (0, -s * (0.35 if mergulho else bater), s * (0.5 if mergulho else 0.1))
        OB['asa_' + lado].scale = (0.6 if mergulho else 1.0, 1, 1)
        OB['mao_' + lado].rotation_euler = (0, -s * bater * 0.4, 0)


previas(OUT, 'gaviao', [
    ('planando', dict(bater=0.08), (0.0, 1.0, 3.2), (0, -0.02, 0.0)),
    ('voo_frente', dict(bater=0.45), (1.2, -1.8, 0.8), (0, -0.05, 0.05)),
    ('mergulho', dict(mergulho=True), (1.7, -0.6, 0.1), (0, -0.05, -0.04)),
    ('cabeca', dict(bater=-0.2), (0.6, -0.75, 0.3), (0, -0.22, 0.1)),
], pose)
