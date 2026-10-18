"""Modela o filhote de bem-te-vi no ninho.

Uso:  blender -b --factory-startup -P arte/modelar_filhote.py -- <pasta_de_saida>
Nós que o jogo controla: cabeca (levanta para pedir comida), mandibula (abre o bico),
olhos_fechados / olhos_abertos e penugem / plumagem_jovem + corpo_jovem (trocados conforme cresce).
"""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aves_comum import *   # noqa: F401,F403

OUT = pasta_saida(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saida'))
random.seed(7)
C = paleta(dict(pele=0xe9b3a0, pele_esc=0xcf9585, penugem=0x857d73, penugem_ponta=0xa8a096, palpebra=0x7a6470,
                bico=0xffcf3a, flange=0xffe15a, boca=0xe8452f, preto=0x1d1712, branco=0xf3efe6, marrom=0x6e5236,
                amarelo=0xf2c41f, olho=0x24150b, pupila=0x050403))
iniciar()

# ---------- corpo e cabeça (pele nua) ----------
corpo = blob('corpo', [
    ((0, 0.0, -0.03), (0.08, 0.095, 0.07), (0, 0, 0)),       # barriga
    ((0, 0.01, 0.0), (0.07, 0.085, 0.06), (0, 0, 0)),        # dorso
    ((0, -0.05, 0.03), (0.05, 0.045, 0.06), (0.4, 0, 0)),    # pescoço
], voxel=0.003, smooth=(0.8, 16), faces=1300)
paint(corpo, lambda p, n: mix(C['pele'], C['pele_esc'], 0.6 * sst(0.2, 0.8, n.z) * sst(-0.05, 0.03, p.y)))

HC = Vector((0, -0.075, 0.085))
NECK = Vector((0, -0.04, 0.04))
cabeca = blob('cabeca_malha', [
    ((0, -0.075, 0.088), (0.066, 0.068, 0.062), (0, 0, 0)),
    ((0, -0.045, 0.055), (0.048, 0.045, 0.05), (0, 0, 0)),
], voxel=0.0024, smooth=(0.8, 16), faces=1500)
paint(cabeca, lambda p, n: mix(C['pele'], C['pele_esc'], 0.35 * sst(0.3, 0.9, n.z)))


# plumagem jovem: camada por cima da pele, com o desenho do bem-te-vi ainda suave
def tinta_jovem_cabeca(p, n):
    d = p - HC
    r = max(d.length, 1e-6)
    e = math.asin(max(-1.0, min(1.0, d.z / r)))
    fw = -d.y / r
    col = mix(C['branco'], C['marrom'], sst(-0.3, -0.5, fw))
    col = mix(col, C['preto'], sst(-0.44, -0.34, e))
    col = mix(col, C['branco'], sst(0.06, 0.16, e))
    return mix(col, C['preto'], sst(0.48, 0.58, e))


jovem = inflar(cabeca, 'plumagem_jovem', 0.0028, tinta_jovem_cabeca)
corpo_jovem = inflar(corpo, 'corpo_jovem', 0.003, lambda p, n: mix(C['amarelo'], C['marrom'], sst(0.05, 0.4, n.z)))

# ---------- olhos ----------
fechados, abertos = Malha(), Malha()
for s in (1, -1):
    a = math.radians(60)
    loc, nor = hit(cabeca, HC, (s * math.sin(a), -math.cos(a), 0.18))
    out = nor.normalized()
    esfera(fechados, loc - out * 0.007, (0.018, 0.02, 0.016), lambda n: C['palpebra'], 12, 8)
    olho(abertos, loc - out * 0.004, out, 0.0135, C['olho'], C['pupila'], C['branco'])

# ---------- bico largo de filhote: bordas amarelas e boca vermelha ----------
loc, nor = hit(cabeca, HC, (0, -1, -0.25))
BEAK_BASE = loc + Vector((0, 0.012, 0.0))
bsup, binf, flanges, boca = Malha(), Malha(), Malha(), Malha()
amarelo_bico = lambda t, sz: mix(C['flange'], C['bico'], sst(0.1, 0.5, t))
bico(bsup, BEAK_BASE, 0.05, 0.085, 0.017, 0.0, 0.002, True, None, cor_fn=amarelo_bico)
bico(binf, BEAK_BASE, 0.045, 0.078, 0.0, 0.015, 0.0, False, None, cor_fn=amarelo_bico)
for s in (1, -1):
    esfera(flanges, BEAK_BASE + Vector((s * 0.04, 0.004, -0.004)), (0.021, 0.016, 0.013), lambda n: C['flange'], 10, 6)
esfera(boca, BEAK_BASE + Vector((0, -0.014, -0.006)), (0.034, 0.026, 0.012), lambda n: C['boca'], 12, 8)

# ---------- penugem: tufos finos na cabeça e no dorso ----------
penugem = Malha()
for k in range(28):
    if k < 16:
        d = Vector((random.uniform(-0.7, 0.7), random.uniform(-0.3, 0.6), 1)).normalized()
        loc, nor = hit(cabeca, HC, d)
    else:
        d = Vector((random.uniform(-0.8, 0.8), random.uniform(-0.2, 0.9), 1)).normalized()
        loc, nor = hit(corpo, Vector((0, 0.01, -0.01)), d)
    if loc is None:
        continue
    dirp = (nor + Vector((random.uniform(-0.4, 0.4), 0.5, 0.3))).normalized()
    pena(penugem, frame(loc - nor * 0.003, dirp, (0, -1, 0.3)), random.uniform(0.024, 0.04), 0.0042,
         C['penugem'], C['penugem_ponta'], C['penugem_ponta'], curva=0.45, arco=0.0, nl=4, nw=1)

# ---------- hierarquia ----------
root = empty('filhote', ZERO)
tronco = empty('tronco', ZERO, root)
corpo.parent = tronco
corpo_jovem.parent = tronco
e_cab = empty('cabeca', NECK, tronco)
for ob in (cabeca, jovem):
    attach(ob, e_cab, NECK)
attach(fechados.obj('olhos_fechados', M['plumagem']), e_cab, NECK)
attach(abertos.obj('olhos_abertos', M['olho']), e_cab, NECK)
attach(flanges.obj('flanges', M['bico']), e_cab, NECK)
attach(boca.obj('boca', M['plumagem']), e_cab, NECK)
attach(bsup.obj('bico_sup', M['bico']), e_cab, NECK)
e_mand = empty('mandibula', BEAK_BASE, e_cab, NECK)
attach(binf.obj('bico_inf', M['bico']), e_mand, BEAK_BASE)
pen = penugem.obj('penugem', M['penas'])
pen.parent = tronco

exportar_glb(os.path.join(OUT, 'filhote.glb'))

# ---------- prévias ----------
OB = bpy.data.objects


def pose(pedir=0.0, crescido=False):
    OB['cabeca'].rotation_euler = (-0.6 * pedir, 0, 0)
    OB['mandibula'].rotation_euler = (0.85 * pedir, 0, 0)
    OB['boca'].hide_render = pedir < 0.2
    for nome in ('plumagem_jovem', 'corpo_jovem', 'olhos_abertos'):
        OB[nome].hide_render = not crescido
    for nome in ('penugem', 'olhos_fechados'):
        OB[nome].hide_render = crescido


previas(OUT, 'filhote', [
    ('recem_nascido', dict(pedir=0.0), (0.42, -0.38, 0.2), (0, -0.04, 0.04)),
    ('pedindo', dict(pedir=1.0), (0.18, -0.5, 0.32), (0, -0.07, 0.08)),
    ('pedindo_perfil', dict(pedir=1.0), (0.55, -0.12, 0.12), (0, -0.05, 0.05)),
    ('crescido', dict(pedir=0.3, crescido=True), (0.35, -0.45, 0.22), (0, -0.05, 0.05)),
], pose)
