"""Modela o tucanuçu (Ramphastos toco), predador de ninhos no jogo.

Uso:  blender -b --factory-startup -P arte/modelar_tucano.py -- <pasta_de_saida>
Nós que o jogo anima: tronco, cabeca, asa_D/asa_E (+ mao_D/mao_E) e cauda.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aves_comum import *   # noqa: F401,F403

OUT = pasta_saida(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saida'))
C = paleta(dict(preto=0x141414, branco=0xf6f1e2, creme=0xf2dc8a, vermelho=0xd22d24, rabadilha=0xf0f0f0,
                laranja=0xff8a1e, amarelo=0xffb238, ponta=0x141110, linha=0x8a3a10, base=0xc9281f,
                pele=0xff9a2e, azul=0x3d7fd6, olho=0x1a1208, pupila=0x050403, pena=0x171717, pena_esc=0x0c0c0c,
                borda=0x2e2e2e, brilho=0xffffff))
iniciar()

# ---------- corpo ----------
corpo = blob('corpo', [
    ((0, 0.0, 0.0), (0.13, 0.21, 0.135), (0, 0, 0)),         # tronco
    ((0, -0.1, 0.0), (0.122, 0.13, 0.13), (0, 0, 0)),        # peito
    ((0, -0.2, 0.075), (0.088, 0.08, 0.092), (0.35, 0, 0)),  # pescoço
    ((0, 0.19, 0.03), (0.07, 0.12, 0.06), (-0.1, 0, 0)),     # uropígio
], voxel=0.0045, smooth=(0.8, 30), faces=3000)


def tinta_corpo(p, n):
    col = C['preto']
    babador = sst(-0.15, -0.45, n.y) * sst(-0.07, 0.0, p.z) * sst(-0.05, -0.13, p.y)   # garganta e papo brancos
    col = mix(col, mix(C['branco'], C['creme'], sst(0.02, -0.06, p.z)), babador)
    if p.y > 0.12 and n.z < -0.1:
        col = mix(col, C['vermelho'], sst(0.12, 0.2, p.y))     # infracaudais vermelhas
    if p.y > 0.2 and n.z > 0.4:
        col = mix(col, C['rabadilha'], sst(0.2, 0.27, p.y))    # uropígio branco
    return col


paint(corpo, tinta_corpo)

# ---------- cabeça, olhos com pele laranja e anel azul ----------
HC = Vector((0, -0.25, 0.14))
NECK = Vector((0, -0.2, 0.11))
cabeca = blob('cabeca_malha', [
    ((0, -0.245, 0.145), (0.1, 0.11, 0.1), (0, 0, 0)),
    ((0, -0.28, 0.115), (0.085, 0.08, 0.075), (0, 0, 0)),
    ((0, -0.18, 0.125), (0.085, 0.07, 0.08), (0, 0, 0)),
], voxel=0.0032, smooth=(0.8, 18), faces=2400)
EYE_DIRS = [Vector((s * math.sin(math.radians(68)), -math.cos(math.radians(68)), 0.12)).normalized() for s in (1, -1)]


def tinta_cabeca(p, n):
    d = (p - HC)
    r = max(d.length, 1e-6)
    u = d / r
    e = math.asin(max(-1.0, min(1.0, u.z)))
    col = C['preto']
    col = mix(col, C['branco'], sst(0.05, -0.08, e) * sst(-0.25, -0.05, -u.y))   # bochecha e garganta brancas
    for ed in EYE_DIRS:
        k = u.dot(ed)
        col = mix(col, C['pele'], sst(0.9, 0.93, k))
        col = mix(col, C['azul'], sst(0.965, 0.975, k))
    return col


paint(cabeca, tinta_cabeca)
olhos = Malha()
for ed in EYE_DIRS:
    loc, nor = hit(cabeca, HC, ed)
    olho(olhos, loc - nor * 0.008, nor.normalized(), 0.017, C['olho'], C['pupila'], C['brilho'])

# ---------- bico enorme: laranja, cume amarelado, linha de corte escura, mancha preta na ponta e base vermelha ----------
loc, nor = hit(cabeca, HC, (0, -1, -0.05))
BASE = loc + Vector((0, 0.03, 0.0))
L, W, HU, HL, CURVA = 0.42, 0.085, 0.075, 0.05, 0.07
bicom = Malha()
rings, cols = [], []
NL, NR = 18, 18
for i in range(NL + 1):
    t = i / NL
    w = W * 0.5 * (1 - t) ** 0.65 + 0.001
    hu = HU * (1 - t) ** 0.85 + 0.001
    hl = HL * (1 - t) ** 0.95 + 0.001
    y = BASE.y - L * t
    zc = BASE.z - CURVA * t * t
    for j in range(NR):
        a = 2 * math.pi * j / NR
        sx, sz = math.cos(a), math.sin(a)
        rings.append(Vector((w * sx, y, zc + (hu * sz if sz > 0 else hl * sz))))
        c = mix(C['laranja'], C['amarelo'], sst(0.55, 0.9, sz))
        if abs(sz) < 0.09 and t > 0.05:
            c = C['linha']
        if t > 0.84 and sz > -0.15:
            c = mix(c, C['ponta'], sst(0.84, 0.88, t))
        if t < 0.05:
            c = C['base']
        cols.append(c)
faces = []
for i in range(NL):
    for j in range(NR):
        a = i * NR + j
        b = i * NR + (j + 1) % NR
        faces.append((a, b, b + NR, a + NR))
bicom.add(rings, faces, cols)

# ---------- asas arredondadas e cauda longa, pretas ----------
SHOULDER = Vector((0.1, -0.08, 0.09))
ARM = 0.3


def asa(s):
    braco, mao = Malha(), Malha()
    up = (0, 0, 1)
    esfera(braco, (s * ARM * 0.5, -0.01, 0.005), (ARM * 0.53, 0.04, 0.016), lambda n: C['pena'], 14, 8)
    for i in range(10):
        pena(braco, frame((s * (0.012 + i * ARM / 10), -0.032, 0.012 - 0.0004 * i), (s * 0.12, 1, 0.02), up), 0.08, 0.036,
             C['pena'], C['borda'], C['pena'], curva=0.05, arco=0.3, lado=s, fio=0.8)
    for i in range(10):
        pena(braco, frame((s * (0.004 + i * ARM / 10), 0.004, -0.0006 * i), (s * (0.04 + 0.025 * i), 1, -0.03), up), 0.2, 0.05,
             C['pena'], C['borda'], C['pena_esc'], curva=0.03, arco=0.2, lado=s, fio=0.8)
    for i, Lp in enumerate([0.22, 0.235, 0.25, 0.258, 0.26, 0.255, 0.24, 0.22]):
        th = 1.3 - i * 0.13
        pena(mao, frame((s * (0.004 + 0.007 * i), 0.004 - 0.003 * i, -0.0012 * i), (s * math.cos(th), math.sin(th), -0.02), up),
             Lp, 0.05, C['pena'], C['borda'], C['pena_esc'], curva=0.04, arco=0.2, lado=s, fio=0.8)
    return braco, mao


TAIL = Vector((0, 0.27, 0.045))
cauda = Malha()
for k, sgn in [(3, 1), (3, -1), (2, 1), (2, -1), (1, 1), (1, -1), (0, 1), (0, -1)]:
    phi = sgn * (0.012 + 0.025 * k)
    pena(cauda, frame(TAIL + Vector((sgn * 0.011 * k, 0, -0.002 * (3 - k))), (math.sin(phi), math.cos(phi), 0.08), (0, 0, 1)),
         0.34, 0.05, C['pena'], C['borda'], C['pena_esc'], curva=-0.03, arco=0.2, lado=sgn, fio=0.85)

# ---------- hierarquia ----------
root = empty('tucano', ZERO)
tronco = empty('tronco', ZERO, root)
corpo.parent = tronco
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

exportar_glb(os.path.join(OUT, 'tucano.glb'))

OB = bpy.data.objects


def pose(bater=0.0, cabeca=0.0):
    for lado, s in (('D', 1), ('E', -1)):
        OB['asa_' + lado].rotation_euler = (0, -s * bater, s * 0.1)
        OB['mao_' + lado].rotation_euler = (0, -s * bater * 0.4, 0)
    OB['cabeca'].rotation_euler = (cabeca, 0, 0)


previas(OUT, 'tucano', [
    ('voo_lado', dict(bater=0.2), (1.9, -0.3, 0.4), (0, -0.12, 0.05)),
    ('voo_frente', dict(bater=0.6), (1.0, -1.6, 0.7), (0, -0.12, 0.05)),
    ('voo_cima', dict(bater=0.05), (0.0, 0.8, 3.0), (0, -0.05, 0.0)),
    ('cabeca', dict(bater=-0.3, cabeca=0.1), (0.7, -0.75, 0.3), (0, -0.4, 0.12)),
], pose)
