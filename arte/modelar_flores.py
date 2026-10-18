"""Modela o capim e as flores dos canteiros da praça. O jogo espalha cópias (InstancedMesh) só dentro da grama.

Uso:  blender -b --factory-startup -P arte/modelar_flores.py -- <pasta_de_saida>
Objetos (cada um com a base na origem): capim, capim_alto, margarida, beijo_vermelho, beijo_rosa, cravo, salvia.
"""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
from mathutils import Vector
from aves_comum import lin, paleta, mix, Malha, tubo, esfera, material, colecao, exportar_glb, look, pasta_saida

OUT = pasta_saida(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saida'))
bpy.ops.wm.read_factory_settings(use_empty=True)
MAT = material('planta', 0.85, double=True, spec=0.15)
C = paleta(dict(caule=0x3d7a2e, folha=0x3f8a36, folha_clara=0x7cb850, folha_esc=0x2a6127,
                capim=0x356f28, capim_ponta=0x8fc452, capim_seco=0xc8c06a,
                branco=0xfbfbf4, creme=0xe3e6c8, miolo=0xf2b81a, miolo_esc=0xc0800c,
                vermelho=0xe8323c, vermelho_esc=0xa81e2a, rosa=0xf472b0, rosa_esc=0xc0407a,
                laranja=0xf28a12, amarelo=0xffc21f, roxo=0x5a3fb8, roxo_claro=0x9a80e6))
Z = Vector((0, 0, 1))


# ---------- peças ----------
def petala(m, o, d, s, L, W, c0, c1, up=Z, ergue=0.0, curva=0.0):
    """Pétala ou folha: losango arredondado (4 triângulos). d = direção, s = lado, up = normal da flor."""
    o, d, s, up = Vector(o), Vector(d).normalized(), Vector(s).normalized(), Vector(up).normalized()
    pts = [o,
           o + d * L * 0.35 + s * W * 0.5 + up * ergue * 0.4,
           o + d * L * 0.35 - s * W * 0.5 + up * ergue * 0.4,
           o + d * L * 0.75 + s * W * 0.42 + up * (ergue * 0.8 - curva * 0.5),
           o + d * L * 0.75 - s * W * 0.42 + up * (ergue * 0.8 - curva * 0.5),
           o + d * L + up * (ergue - curva)]
    cm = mix(c0, c1, 0.55)
    m.add(pts, [(0, 1, 2), (1, 3, 4, 2), (3, 5, 4)], [c0, cm, cm, c1, c1, c1])


def eixos(nrm):
    n = Vector(nrm).normalized()
    a1 = Vector((1, 0, 0)) - n * n.x
    if a1.length < 1e-3:
        a1 = Vector((0, 1, 0)) - n * n.y
    a1.normalize()
    return n, a1, n.cross(a1)


def flor(m, c, nrm, k, rc, L, W, c0, c1, ergue=0.0, curva=0.0, fase=0.0):
    n, a1, a2 = eixos(nrm)
    for i in range(k):
        a = 2 * math.pi * i / k + fase
        d = a1 * math.cos(a) + a2 * math.sin(a)
        petala(m, Vector(c) + d * rc, d, n.cross(d), L, W, c0, c1, n, ergue, curva)


def folha(m, o, ang, incl, L, W, c0=None, c1=None, curva=None):
    d = Vector((math.cos(ang), math.sin(ang), incl))
    s = Vector((-math.sin(ang), math.cos(ang), 0))
    petala(m, o, d, s, L, W, c0 or C['folha_esc'], c1 or C['folha'], Z, 0.0, L * 0.3 if curva is None else curva)


def lamina(m, o, ang, h, w, c0, c1, curva):
    """Folha de capim afinando até a ponta, curvada para fora (3 triângulos)."""
    d = Vector((math.cos(ang), math.sin(ang), 0))
    s = Vector((-d.y, d.x, 0))
    o = Vector(o)
    p1 = o + d * curva * 0.3 + Z * h * 0.55
    tip = o + d * curva + Z * h
    cm = mix(c0, c1, 0.5)
    m.add([o - s * w / 2, o + s * w / 2, p1 - s * w * 0.32, p1 + s * w * 0.32, tip], [(0, 1, 3, 2), (2, 3, 4)], [c0, c0, cm, cm, c1])


# ---------- espécies ----------
def capim(nome, n, hmin, hmax, seed, seco=0.0):
    rnd = random.Random(seed)
    m = Malha()
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.35, 0.35)
        h = rnd.uniform(hmin, hmax)
        ponta = mix(C['capim_ponta'], C['capim_seco'], rnd.uniform(0, seco))
        lamina(m, (math.cos(a) * 0.012, math.sin(a) * 0.012, 0), a, h, rnd.uniform(0.012, 0.017), C['capim'], ponta,
               h * rnd.uniform(0.15, 0.42))
    return m.obj(nome, MAT)


def margarida():
    m = Malha()
    top = Vector((0.014, 0.006, 0.26))
    tubo(m, [(0, 0, 0), (0.004, 0.002, 0.09), (0.01, 0.004, 0.18), top], [0.005, 0.0045, 0.004, 0.0035], [C['caule']] * 4, seg=4)
    for h, a in ((0.02, 0.4), (0.05, 2.6), (0.03, 4.4)):
        folha(m, (0, 0, h), a, 0.8, 0.085, 0.022)
    nrm = Vector((0.3, 0.12, 1))
    flor(m, top, nrm, 13, 0.011, 0.05, 0.016, C['creme'], C['branco'], ergue=0.006, curva=0.008)
    esfera(m, top + nrm.normalized() * 0.003, (0.015, 0.015, 0.009), lambda q: mix(C['miolo_esc'], C['miolo'], 0.5 + 0.5 * q.z), 6, 3)
    return m.obj('margarida', MAT)


def beijo(nome, cor, cor_esc, seed):
    """Maria-sem-vergonha (beijo): touceira baixa de folhas largas com flores de 5 pétalas."""
    rnd = random.Random(seed)
    m = Malha()
    for i in range(7):
        a = 2 * math.pi * i / 7 + rnd.uniform(-0.2, 0.2)
        folha(m, (0, 0, 0.01), a, rnd.uniform(0.3, 0.6), rnd.uniform(0.08, 0.1), 0.046)
    for i in range(3):
        folha(m, (0, 0, 0.04), 2 * math.pi * i / 3 + 0.3, rnd.uniform(0.7, 1.0), 0.065, 0.038, C['folha'], C['folha_clara'])
    for j in range(5):
        a, r = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.0, 0.065)
        c = Vector((math.cos(a) * r, math.sin(a) * r, rnd.uniform(0.085, 0.115)))
        tubo(m, [(0, 0, 0.03), c - Vector((0, 0, 0.004))], [0.003, 0.0025], [C['caule']] * 2, seg=3)
        nrm = Vector((c.x * 4, c.y * 4, 1))
        flor(m, c, nrm, 5, 0.002, 0.028, 0.027, cor_esc, cor, ergue=0.004, curva=0.002, fase=rnd.uniform(0, 1))
    return m.obj(nome, MAT)


def cravo():
    """Cravo-de-defunto: pompons laranja e amarelos sobre folhas recortadas."""
    rnd = random.Random(5)
    m = Malha()
    for i in range(8):
        folha(m, (0, 0, 0.01), 2 * math.pi * i / 8 + rnd.uniform(-0.2, 0.2), rnd.uniform(0.5, 0.9), rnd.uniform(0.08, 0.1), 0.03)
    for j in range(3):
        a = 2 * math.pi * j / 3 + rnd.uniform(-0.3, 0.3)
        c = Vector((math.cos(a) * 0.035, math.sin(a) * 0.035, rnd.uniform(0.15, 0.19)))
        tubo(m, [(0, 0, 0.02), (c.x * 0.5, c.y * 0.5, c.z * 0.6), c - Vector((0, 0, 0.02))], [0.004, 0.0035, 0.003], [C['caule']] * 3, seg=3)
        esfera(m, c, (0.028, 0.028, 0.022), lambda q: mix(C['laranja'], C['amarelo'], 0.3 + 0.5 * q.z), 7, 4)
        flor(m, c - Vector((0, 0, 0.006)), Z, 6, 0.016, 0.022, 0.02, C['laranja'], C['amarelo'], ergue=0.006)
    return m.obj('cravo', MAT)


def salvia():
    """Sálvia azul: hastes eretas com espigas roxas."""
    rnd = random.Random(9)
    m = Malha()
    for i in range(6):
        folha(m, (0, 0, 0.01), 2 * math.pi * i / 6 + rnd.uniform(-0.3, 0.3), rnd.uniform(0.4, 0.8), 0.08, 0.028)
    for j in range(4):
        a = 2 * math.pi * j / 4 + rnd.uniform(-0.3, 0.3)
        h, lean = rnd.uniform(0.28, 0.36), rnd.uniform(0.02, 0.05)
        top = Vector((math.cos(a) * lean, math.sin(a) * lean, h))
        mid = top * 0.5
        tubo(m, [(0, 0, 0.0), mid], [0.0035, 0.003], [C['caule']] * 2, seg=3)
        pts = [mid.lerp(top, t) for t in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
        rs = [0.004, 0.012, 0.009, 0.011, 0.007, 0.002]
        tubo(m, pts, rs, [mix(C['roxo'], C['roxo_claro'], i / 5) for i in range(6)], seg=4)
    return m.obj('salvia', MAT)


plantas = [capim('capim', 7, 0.13, 0.22, 1), capim('capim_alto', 9, 0.22, 0.38, 2, seco=0.8), margarida(),
           beijo('beijo_vermelho', C['vermelho'], C['vermelho_esc'], 11), beijo('beijo_rosa', C['rosa'], C['rosa_esc'], 12),
           cravo(), salvia()]
for o in plantas:
    print('PLANTA', o.name, 'triangulos', sum(len(p.vertices) - 2 for p in o.data.polygons))
exportar_glb(os.path.join(OUT, 'flores.glb'))

# ---------- prévias: uma fileira com cada planta e um canteiro de exemplo ----------
objs = {o.name: o for o in plantas}
ordem = ['capim', 'capim_alto', 'margarida', 'beijo_vermelho', 'beijo_rosa', 'cravo', 'salvia']
for i, nome in enumerate(ordem):
    objs[nome].location = (i * 0.2 - 0.6, 0, 0)
rnd = random.Random(4)


def copia(nome, x, y, s=1.0):
    o = objs[nome].copy()
    o.location = (x, y, 0)
    o.rotation_euler = (0, 0, rnd.uniform(0, 2 * math.pi))
    o.scale = (s, s, s)
    colecao().objects.link(o)


for cx, cy, nome in ((-0.9, 1.2, 'beijo_vermelho'), (0.0, 1.5, 'salvia'), (0.9, 1.2, 'cravo'), (-0.4, 2.3, 'beijo_rosa'), (0.6, 2.4, 'margarida')):
    for _ in range(16):
        a, r = rnd.uniform(0, 2 * math.pi), 0.42 * math.sqrt(rnd.random())
        copia(nome, cx + math.cos(a) * r, cy + math.sin(a) * r, rnd.uniform(0.85, 1.15))
for _ in range(260):
    copia('capim' if rnd.random() < 0.75 else 'capim_alto', rnd.uniform(-1.8, 1.8), rnd.uniform(0.45, 3.2), rnd.uniform(0.8, 1.2))
for _ in range(20):
    copia('margarida', rnd.uniform(-1.6, 1.6), rnd.uniform(0.5, 3.0), rnd.uniform(0.85, 1.1))

chao = bpy.data.meshes.new('chao')
chao.from_pydata([(-4, -2, 0), (4, -2, 0), (4, 6, 0), (-4, 6, 0)], [], [(0, 1, 2, 3)])
mg = bpy.data.materials.new('grama')
mg.use_nodes = True
mg.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*lin(0x5f9e45), 1)
mg.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 1.0
chao.materials.append(mg)
colecao().objects.link(bpy.data.objects.new('chao', chao))

sc = bpy.context.scene
engines = bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys()
sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
W, H = 700, 520
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
try:
    sc.view_settings.view_transform = 'Standard'
except Exception:
    pass
world = bpy.data.worlds.new('ceu')
sc.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (*lin(0xbfe0f5), 1)
sol = bpy.data.lights.new('sol', 'SUN')
sol.energy = 3.2
so = bpy.data.objects.new('sol', sol)
so.rotation_euler = (math.radians(42), 0, math.radians(30))
colecao().objects.link(so)
cd = bpy.data.cameras.new('cam')
cam = bpy.data.objects.new('cam', cd)
colecao().objects.link(cam)
sc.camera = cam
paths = []
for nome, lens, pos, alvo in (('fileira', 50, (0, -1.05, 0.32), (0, 0, 0.13)), ('canteiro', 30, (0, -0.9, 1.5), (0, 1.7, 0)),
                              ('perto', 40, (0.5, 0.35, 0.32), (-0.2, 1.35, 0.08))):
    cd.lens = lens
    look(cam, pos, alvo)
    sc.render.filepath = os.path.join(OUT, 'previa_flores_%s.png' % nome)
    bpy.ops.render.render(write_still=True)
    paths.append(sc.render.filepath)
grid = np.ones((H, W * len(paths), 4), dtype=np.float32)
for i, p in enumerate(paths):
    im = bpy.data.images.load(p)
    grid[:, i * W:(i + 1) * W] = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)
img = bpy.data.images.new('folha', W * len(paths), H, alpha=True)
img.pixels = grid.ravel()
img.filepath_raw = os.path.join(OUT, 'previa_flores.png')
img.file_format = 'PNG'
img.save()
print('FOLHA', img.filepath_raw)
