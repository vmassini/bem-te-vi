"""Modela o cenário da praça: prédios e casas em volta, árvores, postes, bancos, banca, coreto, carros e chafariz.

Uso:  blender -b --factory-startup -P arte/modelar_praca.py -- <pasta_de_saida>
Tudo é montado em coordenadas do jogo (x, y para cima, z) e só vira coordenada do Blender (x, -z, y) ao criar a malha;
o glTF exportado volta exatamente para as coordenadas do jogo.
As medidas usadas para pousar (topo dos postes 4,48 m, encosto dos bancos 0,94 m, teto da banca 2,3 m, teto dos carros 1,46 m,
borda do chafariz 0,95 m, galhos da árvore do ninho e fios da rua norte) seguem as constantes de src/jogo.html.
Nós exportados: predios_norte/sul/oeste/leste, vidros, luzes, fios, moveis, chafariz, troncos, copas, copas_rua, arvore_ninho, copa_ninho e colisao (invisível).
Sombreamento facetado: o .glb sai sem normais e o jogo usa flatShading.
"""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix, Quaternion, noise
from aves_comum import lin, mix, sst, set_colors, colecao, pasta_saida, material, look

OUT = pasta_saida(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saida'))
bpy.ops.wm.read_factory_settings(use_empty=True)
random.seed(2026)

MAT = {
    'cenario': material('cenario', 0.85, double=True, spec=0.15),
    'vidro': material('vidro', 0.12, double=True, spec=0.8),
    'luz': material('luz', 0.4, double=True),
    'folhas': material('folhas', 0.9, double=True, spec=0.1),
    'fio': material('fio', 0.6, double=True),
    'colisao': material('colisao', 1.0, double=True),
    'contexto': material('contexto', 0.95, double=True, spec=0.05),
}
_b = MAT['luz'].node_tree.nodes['Principled BSDF']
if 'Emission Strength' in _b.inputs:
    _vc = [n for n in MAT['luz'].node_tree.nodes if n.type == 'VERTEX_COLOR'][0]
    MAT['luz'].node_tree.links.new(_vc.outputs['Color'], _b.inputs['Emission Color'])
    _b.inputs['Emission Strength'].default_value = 1.2


# ---------- cores ----------
def C(h):
    return lin(h)


def esc(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def var(c, a=0.07):
    return esc(c, 1 + random.uniform(-a, a))


BRANCO = C(0xf3f1ea)


# ---------- geometria em coordenadas do jogo ----------
ID = lambda p: p


def TF(px=0.0, py=0.0, pz=0.0, ry=0.0):
    c, s = math.cos(ry), math.sin(ry)
    return lambda p: (px + p[0] * c + p[2] * s, py + p[1], pz - p[0] * s + p[2] * c)


def comp(f, g):
    return lambda p: f(g(p))


class Geo:
    def __init__(self):
        self.v, self.f, self.c = [], [], []

    def add(self, verts, faces, cols):
        o = len(self.v)
        self.v.extend(verts)
        self.c.extend(cols)
        self.f.extend(tuple(i + o for i in fc) for fc in faces)

    def obj(self, name, mat):
        me = bpy.data.meshes.new(name)
        me.from_pydata([(x, -z, y) for (x, y, z) in self.v], [], self.f)
        me.update()
        set_colors(me, self.c)
        me.materials.append(MAT[mat])
        ob = bpy.data.objects.new(name, me)
        colecao().objects.link(ob)
        return ob


def box(g, c, s, col, tf=ID):
    hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
    vs = [(c[0] + dx * hx, c[1] + dy * hy, c[2] + dz * hz) for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    g.add([tf(v) for v in vs], [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)], [col] * 8)


def box2(g, x0, y0, z0, x1, y1, z1, col, tf=ID):
    box(g, ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)), col, tf)


def quad(g, a, b, c, d, col, tf=ID):
    g.add([tf(a), tf(b), tf(c), tf(d)], [(0, 1, 2, 3)], [col] * 4)


def viga(g, p0, p1, w, h, col, tf=ID):
    """Caixa deitada entre dois pontos (eixo horizontal)."""
    dx, dz = p1[0] - p0[0], p1[2] - p0[2]
    L = math.hypot(dx, dz)
    c = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
    box(g, (0, 0, 0), (w, h, L), col, comp(tf, TF(c[0], c[1], c[2], math.atan2(dx, dz))))


def lathe(g, prof, col, seg=12, tf=ID, c=(0, 0, 0), tampa=False, fundo=False, fase=0.0):
    """Superfície de revolução em torno do eixo y. prof = [(raio, y)] de baixo para cima; col pode ser f(i, r, y)."""
    verts, cols, faces, rings = [], [], [], []
    for i, (r, y) in enumerate(prof):
        cc = col(i, r, y) if callable(col) else col
        if r < 1e-5:
            rings.append([len(verts)])
            verts.append(tf((c[0], c[1] + y, c[2])))
            cols.append(cc)
            continue
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg + fase
            ring.append(len(verts))
            verts.append(tf((c[0] + r * math.cos(a), c[1] + y, c[2] + r * math.sin(a))))
            cols.append(cc)
        rings.append(ring)
    for i in range(len(rings) - 1):
        A, B = rings[i], rings[i + 1]
        if len(A) == 1 and len(B) == 1:
            continue
        for k in range(seg):
            if len(A) == 1:
                faces.append((A[0], B[k], B[(k + 1) % seg]))
            elif len(B) == 1:
                faces.append((A[k], B[0], A[(k + 1) % seg]))
            else:
                faces.append((A[k], B[k], B[(k + 1) % seg], A[(k + 1) % seg]))
    for flag, ring, y in ((tampa, rings[-1], prof[-1][1]), (fundo, rings[0], prof[0][1])):
        if flag and len(ring) > 1:
            ci = len(verts)
            verts.append(tf((c[0], c[1] + y, c[2])))
            cols.append(cols[ring[0]])
            for k in range(seg):
                faces.append((ci, ring[(k + 1) % seg], ring[k]) if ring is rings[-1] else (ci, ring[k], ring[(k + 1) % seg]))
    g.add(verts, faces, cols)


def tubo(g, pts, raios, col, seg=6, tf=ID, tampas=True):
    pts = [Vector(p) for p in pts]
    n = len(pts)
    verts, cols, faces = [], [], []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = Vector((0, 1, 0)) if abs(t.y) < 0.9 else Vector((1, 0, 0))
        u = t.cross(a).normalized()
        v = t.cross(u)
        cc = col(i) if callable(col) else col
        for k in range(seg):
            ang = 2 * math.pi * k / seg
            q = p + (u * math.cos(ang) + v * math.sin(ang)) * raios[i]
            verts.append(tf(tuple(q)))
            cols.append(cc)
    for i in range(n - 1):
        for k in range(seg):
            a = i * seg + k
            b = i * seg + (k + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    if tampas:
        for idx, base in ((0, 0), (n - 1, (n - 1) * seg)):
            ci = len(verts)
            verts.append(tf(tuple(pts[idx])))
            cols.append(cols[base])
            for k in range(seg):
                faces.append((ci, base + (k + 1) % seg, base + k) if idx == 0 else (ci, base + k, base + (k + 1) % seg))
    g.add(verts, faces, cols)


def prisma(g, poly, a0, a1, col, tf=ID, eixo='z'):
    """Polígono 2D extrudado. eixo 'z': poly em (x, y); eixo 'x': poly em (z, y)."""
    P = (lambda u, v, w: (u, v, w)) if eixo == 'z' else (lambda u, v, w: (w, v, u))
    n = len(poly)
    verts = [tf(P(u, v, a0)) for (u, v) in poly] + [tf(P(u, v, a1)) for (u, v) in poly]
    faces = [tuple(range(n, 2 * n)), tuple(reversed(range(n)))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    g.add(verts, faces, [col] * (2 * n))


def moldura(g, x0, y0, x1, y1, t, z, p, col, tf=ID):
    """Moldura retangular saliente no plano z (frente para +z)."""
    O = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    I = [(x0 + t, y0 + t), (x1 - t, y0 + t), (x1 - t, y1 - t), (x0 + t, y1 - t)]
    verts = [(x, y, z + p) for x, y in O] + [(x, y, z + p) for x, y in I] + [(x, y, z) for x, y in O] + [(x, y, z) for x, y in I]
    faces = []
    for k in range(4):
        j = (k + 1) % 4
        faces.append((k, j, 4 + j, 4 + k))           # frente
        faces.append((8 + k, 8 + j, j, k))           # lado de fora
        faces.append((4 + k, 4 + j, 12 + j, 12 + k))  # lado de dentro
    g.add([tf(v) for v in verts], faces, [col] * 16)


def groundY(x, z):
    ax, az = abs(x), abs(z)
    if ax <= 18.5 and az <= 18.5:
        if math.hypot(x, z) <= 6.6:
            return 0.23
        if 1.65 <= ax <= 17.05 and 1.65 <= az <= 17.05:
            return 0.21
        return 0.15
    if ax >= 26.5 or az >= 26.5:
        return 0.14
    return 0.0


# acumuladores (um objeto exportado cada)
PRED, VIDRO, LUZ, FIO, MOV, CHAF, TRONCO, COPA, COPA_RUA, ARV_N, COPA_N, COLI, CTX = (Geo() for _ in range(13))
LADOS_PRED = {'predios_norte': Geo(), 'predios_sul': Geo(), 'predios_oeste': Geo(), 'predios_leste': Geo()}  # PRED aponta para o lado em construção

# =====================================================================
# PRÉDIOS, SOBRADOS E CASAS
# =====================================================================
FACH = [0xf2c14e, 0x7fb7be, 0xe88d72, 0xf4e9d8, 0xa3c4bc, 0xd9a5b3, 0xb8d8ba, 0xf6d6a8, 0x9fb4d9, 0xe7e0cf,
        0xf3efe6, 0xc2b0d6, 0xe9c46a, 0x8fbfa8, 0xd98c5f, 0xb7cfe0]
VIDROS = [0x5c6f86, 0x6f8aa6, 0x4a5c70, 0x8aa4bd, 0x7b93a8, 0xcbbf98, 0x9a8a6a]
TOLDOS = [(0xd8402a, 0xf6efe2), (0x2f6fb3, 0xf6efe2), (0x3fae6a, 0xf6efe2), (0xff8c42, 0xfff3d6), (0x8a3b6f, 0xf6efe2), (0x1f5f4a, 0xf2c12e)]
PLACAS = [0xd8402a, 0x2f6fb3, 0xffd21f, 0x3fae6a, 0xff8c42, 0xf6efe2, 0x2b2b2b, 0x8a3b6f]
VENEZ = [0x2e7d5b, 0x2f6fb3, 0x7a4b2a, 0xb5473a, 0x3a6b8f, 0x5b7f3a, 0x2b4d6b]
METAL = C(0x3d4247)


def janela(x, y, ww, wh, zf, tf, mold, vid, peitoril=None, venez=None, div=True):
    t = 0.08
    moldura(PRED, x - ww / 2, y, x + ww / 2, y + wh, t, zf, 0.06, mold, tf)
    quad(VIDRO, (x - ww / 2 + t, y + t, zf + 0.015), (x + ww / 2 - t, y + t, zf + 0.015),
         (x + ww / 2 - t, y + wh - t, zf + 0.015), (x - ww / 2 + t, y + wh - t, zf + 0.015), vid, tf)
    if div:
        box2(PRED, x - 0.022, y + t, zf, x + 0.022, y + wh - t, zf + 0.04, mold, tf)
        box2(PRED, x - ww / 2 + t, y + wh * 0.62 - 0.02, zf, x + ww / 2 - t, y + wh * 0.62 + 0.02, zf + 0.04, mold, tf)
    if peitoril:
        box2(PRED, x - ww / 2 - 0.07, y - 0.07, zf, x + ww / 2 + 0.07, y + 0.01, zf + 0.13, peitoril, tf)
    if venez:  # folhas abertas encostadas na parede, com ripas
        for s in (-1, 1):
            xa, xb = sorted((x + s * (ww / 2 + 0.02), x + s * (ww / 2 + ww / 2 + 0.02)))
            box2(PRED, xa, y + 0.03, zf, xb, y + wh - 0.03, zf + 0.04, venez, tf)
            esc_v = esc(venez, 0.62)
            for k in range(1, 7):
                yy = y + 0.03 + (wh - 0.06) * k / 7
                quad(PRED, (xa + 0.04, yy - 0.015, zf + 0.042), (xb - 0.04, yy - 0.015, zf + 0.042),
                     (xb - 0.04, yy + 0.015, zf + 0.042), (xa + 0.04, yy + 0.015, zf + 0.042), esc_v, tf)


def porta(x, y, pw, ph, zf, tf, mold, cor):
    moldura(PRED, x - pw / 2, y, x + pw / 2, y + ph, 0.1, zf, 0.07, mold, tf)
    box2(PRED, x - pw / 2 + 0.1, y, zf, x + pw / 2 - 0.1, y + ph - 0.1, zf + 0.03, cor, tf)
    for yy in (0.25, 1.15):
        box2(PRED, x - pw / 2 + 0.2, y + yy, zf + 0.03, x + pw / 2 - 0.2, y + yy + 0.75, zf + 0.05, esc(cor, 0.82), tf)
    box2(PRED, x + pw / 2 - 0.26, y + 1.0, zf + 0.03, x + pw / 2 - 0.2, y + 1.08, zf + 0.09, C(0xd9b44a), tf)


def toldo(x0, x1, y_top, zf, prof, queda, cores, tf, aba=0.2):
    n = max(2, int((x1 - x0) / 0.34))
    cs = [C(cores[0]), C(cores[1])]
    for i in range(n):
        xa = x0 + (x1 - x0) * i / n
        xb = x0 + (x1 - x0) * (i + 1) / n
        c = cs[i % 2]
        quad(PRED, (xa, y_top, zf), (xb, y_top, zf), (xb, y_top - queda, zf + prof), (xa, y_top - queda, zf + prof), c, tf)
        quad(PRED, (xa, y_top - queda, zf + prof), (xb, y_top - queda, zf + prof),
             (xb, y_top - queda - aba, zf + prof), (xa, y_top - queda - aba, zf + prof), c, tf)
    for xs in (x0, x1):
        PRED.add([tf((xs, y_top, zf)), tf((xs, y_top - queda - aba, zf + prof)), tf((xs, y_top - queda, zf))],
                 [(0, 1, 2)], [cs[0]] * 3)


def letreiro(x0, x1, y0, y1, zf, tf, cor):
    box2(PRED, x0, y0, zf, x1, y1, zf + 0.1, cor, tf)
    claro = mix(cor, BRANCO, 0.75) if sum(cor) < 1.2 else esc(cor, 0.25)
    n = max(3, int((x1 - x0 - 0.6) / 0.32))
    for i in range(n):  # "letras" em blocos
        xc = x0 + 0.3 + (x1 - x0 - 0.6) * (i + 0.5) / n
        hh = (y1 - y0) * random.choice((0.42, 0.5, 0.56))
        box2(PRED, xc - 0.1, (y0 + y1) / 2 - hh / 2, zf + 0.1, xc + 0.1, (y0 + y1) / 2 + hh / 2, zf + 0.13, claro, tf)


def loja(w, zf, tf, cor, hl=3.9, com_toldo=True):
    x0, x1 = -w / 2 + 0.4, w / 2 - 0.4
    box2(PRED, -w / 2 - 0.02, 0, zf, w / 2 + 0.02, 0.42, zf + 0.06, esc(cor, 0.68), tf)
    vit = C(random.choice([0x9fb3c4, 0xb9c6cf, 0xd6c9a6, 0x8fa5b5]))
    quad(VIDRO, (x0, 0.42, zf + 0.012), (x1, 0.42, zf + 0.012), (x1, 2.95, zf + 0.012), (x0, 2.95, zf + 0.012), vit, tf)
    n = max(2, round((x1 - x0) / 1.6))
    for i in range(n + 1):
        xm = x0 + i * (x1 - x0) / n
        box2(PRED, xm - 0.045, 0.42, zf, xm + 0.045, 2.95, zf + 0.06, METAL, tf)
    box2(PRED, x0, 2.92, zf, x1, 3.02, zf + 0.06, METAL, tf)
    box2(PRED, x0, 0.42, zf, x1, 0.5, zf + 0.06, METAL, tf)
    porta_x = x0 + (x1 - x0) * (random.randint(0, n - 1) + 0.5) / n
    quad(PRED, (porta_x - 0.45, 0.5, zf + 0.02), (porta_x + 0.45, 0.5, zf + 0.02), (porta_x + 0.45, 2.85, zf + 0.02),
         (porta_x - 0.45, 2.85, zf + 0.02), C(0x3b4a57), tf)
    letreiro(x0 + 0.1, x1 - 0.1, 3.15, 3.75, zf, tf, C(random.choice(PLACAS)))
    if com_toldo:
        toldo(x0, x1, 3.08, zf + 0.02, 1.15, 0.5, random.choice(TOLDOS), tf)


def sacada(x, y, bw, zf, tf, estilo, laje):
    p = 0.8 if estilo != 'ferro' else 0.5
    box2(PRED, x - bw / 2, y - 0.02, zf, x + bw / 2, y + 0.12, zf + p, laje, tf)
    if estilo == 'vidro':
        quad(VIDRO, (x - bw / 2 + 0.03, y + 0.12, zf + p - 0.03), (x + bw / 2 - 0.03, y + 0.12, zf + p - 0.03),
             (x + bw / 2 - 0.03, y + 1.0, zf + p - 0.03), (x - bw / 2 + 0.03, y + 1.0, zf + p - 0.03), C(0x9cc6cf), tf)
        box2(PRED, x - bw / 2, y + 1.0, zf + p - 0.06, x + bw / 2, y + 1.06, zf + p, METAL, tf)
    elif estilo == 'parapeito':
        box2(PRED, x - bw / 2, y + 0.12, zf + p - 0.1, x + bw / 2, y + 1.0, zf + p, laje, tf)
    else:
        box2(PRED, x - bw / 2, y + 0.95, zf + p - 0.04, x + bw / 2, y + 1.0, zf + p, METAL, tf)
        n = int(bw / 0.13)
        for i in range(n + 1):
            xb = x - bw / 2 + bw * i / n
            quad(PRED, (xb - 0.013, y + 0.12, zf + p - 0.02), (xb + 0.013, y + 0.12, zf + p - 0.02),
                 (xb + 0.013, y + 0.95, zf + p - 0.02), (xb - 0.013, y + 0.95, zf + p - 0.02), METAL, tf)
        for s in (-1, 1):
            box2(PRED, x + s * bw / 2 - 0.02, y + 0.12, zf, x + s * bw / 2 + 0.02, y + 1.0, zf + p, METAL, tf)


def ar_cond(x, y, zf, tf):
    box2(PRED, x - 0.35, y, zf, x + 0.35, y + 0.45, zf + 0.36, C(0xe3e3de), tf)
    quad(PRED, (x - 0.3, y + 0.05, zf + 0.362), (x + 0.3, y + 0.05, zf + 0.362), (x + 0.3, y + 0.4, zf + 0.362),
         (x - 0.3, y + 0.4, zf + 0.362), C(0x8f8f8a), tf)


def parapeito(w, d, h, cor, tf, alt=0.5):
    e = 0.16
    box2(PRED, -w / 2, h, -d / 2, w / 2, h + alt, -d / 2 + e, cor, tf)
    box2(PRED, -w / 2, h, d / 2 - e, w / 2, h + alt, d / 2, cor, tf)
    box2(PRED, -w / 2, h, -d / 2, -w / 2 + e, h + alt, d / 2, cor, tf)
    box2(PRED, w / 2 - e, h, -d / 2, w / 2, h + alt, d / 2, cor, tf)
    box2(PRED, -w / 2 + e, h, -d / 2 + e, w / 2 - e, h + 0.03, d / 2 - e, var(C(0x8d8a85), 0.1), tf)


def janelas_laterais(L, tf, y0, passo, n, mold, vid):
    """Janelas nas paredes laterais, só nos andares acima do vizinho."""
    w, d = L['w'], L['d']
    for s, nh in ((-1, L['viz'][0]), (1, L['viz'][1])):
        for k in range(n):
            y = y0 + passo * k
            if y < nh + 0.4:
                continue
            for zc in (d / 2 - 1.8, d / 2 - 4.4):
                if zc < -d / 2 + 1:
                    continue
                tl = comp(tf, TF(s * w / 2, 0, zc, s * math.pi / 2))
                janela(0, y + 0.9, 1.1, 1.4, 0.0, tl, mold, vid, mold, div=False)


def predio(L):
    w, d, h, n = L['w'], L['d'], L['h'], L['andares']
    tf = TF(L['cx'], 0, L['cz'], L['rot'])
    zf = d / 2
    cor = var(C(L['cor']), 0.05)
    clara = mix(cor, BRANCO, 0.5)
    box2(PRED, -w / 2, 0, -d / 2, w / 2, h, d / 2, cor, tf)
    marquise = random.random() < 0.4
    loja(w, zf, tf, cor, com_toldo=not marquise)
    box2(PRED, -w / 2, 3.95, zf, w / 2, 4.2, zf + (1.0 if marquise else 0.12), clara, tf)
    estilo = random.choice(['janelas', 'janelas', 'varandas', 'varandas_alt', 'faixas'])
    guarda = random.choice(['vidro', 'ferro', 'parapeito'])
    cols = max(1, round((w - 1.0) / 2.6))
    passo = w / cols
    vid = C(random.choice(VIDROS[:5]))
    mold = C(random.choice([0xf3f1ea, 0xe0ddd5, 0x3d4247, 0x8a7b6a, 0xd9d4c7]))
    ww = min(1.6, passo - 0.7)
    for k in range(n - 1):
        y = 4.2 + 3.0 * k
        box2(PRED, -w / 2 - 0.04, y - 0.07, zf - 0.02, w / 2 + 0.04, y + 0.07, zf + 0.08, clara, tf)
        if estilo == 'faixas':
            box2(PRED, -w / 2 - 0.02, y + 0.95, zf - 0.02, w / 2 + 0.02, y + 2.35, zf + 0.025, esc(cor, 0.9), tf)
        for i in range(cols):
            x = -w / 2 + passo * (i + 0.5)
            v = vid if random.random() > 0.15 else C(random.choice(VIDROS))
            if estilo == 'varandas' or (estilo == 'varandas_alt' and (i + k) % 2 == 0):
                bw = min(passo - 0.3, 2.3)
                janela(x, y + 0.12, bw - 0.5, 2.3, zf, tf, mold, v)
                sacada(x, y, bw, zf, tf, guarda, clara)
            else:
                janela(x, y + 0.9, ww, 1.5, zf, tf, mold, v, clara)
                if random.random() < 0.2:
                    ar_cond(x + ww / 2 + 0.5, y + 0.35, zf, tf)
    box2(PRED, -w / 2 - 0.12, h - 0.45, zf - 0.3, w / 2 + 0.12, h, zf + 0.2, clara, tf)
    parapeito(w, d, h, cor, tf)
    # caixa-d'água e casa de máquinas no telhado
    cx = random.uniform(-w / 2 + 1.5, w / 2 - 2.5)
    cz = random.uniform(-d / 2 + 1.2, -0.5)
    concreto = var(C(0xbab6ad), 0.06)
    box2(PRED, cx, h, cz, cx + 2.2, h + 1.9, cz + 2.0, concreto, tf)
    box2(PRED, cx - 0.1, h + 1.9, cz - 0.1, cx + 2.3, h + 2.02, cz + 2.1, esc(concreto, 0.85), tf)
    if random.random() < 0.6:
        tubo(PRED, [(cx + 1.0, h + 2.0, cz + 1.0), (cx + 1.0, h + 4.2, cz + 1.0)], [0.03, 0.02], C(0x777777), 4, tf)
        for yy, ll in ((h + 3.4, 0.7), (h + 3.9, 0.5)):
            box2(PRED, cx + 1.0 - ll, yy, cz + 0.98, cx + 1.0 + ll, yy + 0.03, cz + 1.02, C(0x777777), tf)
    janelas_laterais(L, tf, 4.2, 3.0, n - 1, mold, vid)
    box2(COLI, -w / 2, 0, -d / 2, w / 2, h + 0.5, d / 2, BRANCO, tf)


def sobrado(L):
    w, d, h, n = L['w'], L['d'], L['h'], L['andares']
    tf = TF(L['cx'], 0, L['cz'], L['rot'])
    zf = d / 2
    cor = var(C(L['cor']), 0.05)
    clara = mix(cor, BRANCO, 0.55)
    box2(PRED, -w / 2, 0, -d / 2, w / 2, h, d / 2, cor, tf)
    if random.random() < 0.6:
        loja(w, zf, tf, cor, hl=3.4, com_toldo=random.random() < 0.7)
    else:  # porta de enrolar
        x0, x1 = -w / 2 + 0.5, w / 2 - 0.5
        cinza = var(C(0x9aa0a6), 0.05)
        box2(PRED, x0, 0, zf, x1, 3.0, zf + 0.05, cinza, tf)
        for k in range(1, 22):
            yy = 3.0 * k / 22
            quad(PRED, (x0, yy - 0.012, zf + 0.052), (x1, yy - 0.012, zf + 0.052), (x1, yy + 0.012, zf + 0.052),
                 (x0, yy + 0.012, zf + 0.052), esc(cinza, 0.7), tf)
        box2(PRED, x0 - 0.05, 3.0, zf, x1 + 0.05, 3.25, zf + 0.12, esc(cinza, 0.8), tf)
        letreiro(x0, x1, 3.35, 3.85, zf, tf, C(random.choice(PLACAS)))
    cols = max(1, round(w / 2.5))
    passo = w / cols
    mold = BRANCO if random.random() < 0.7 else C(0xe6d7b8)
    vz = C(random.choice(VENEZ))
    vid = C(random.choice(VIDROS))
    for k in range(1, n):
        y = 3.6 * k
        box2(PRED, -w / 2 - 0.05, y - 0.1, zf - 0.02, w / 2 + 0.05, y + 0.1, zf + 0.12, clara, tf)
        for i in range(cols):
            x = -w / 2 + passo * (i + 0.5)
            if random.random() < 0.45:
                janela(x, y + 0.2, 1.0, 2.3, zf, tf, mold, vid)
                sacada(x, y + 0.05, 1.5, zf, tf, 'ferro', clara)
            else:
                janela(x, y + 0.95, 1.0, 1.6, zf, tf, mold, vid, clara, venez=vz if random.random() < 0.7 else None)
    # platibanda com frontão no meio
    y = 3.6 * n
    box2(PRED, -w / 2 - 0.1, y - 0.15, zf - 0.02, w / 2 + 0.1, y + 0.15, zf + 0.22, clara, tf)
    box2(PRED, -w / 2 - 0.06, h - 0.12, zf - 0.02, w / 2 + 0.06, h, zf + 0.14, clara, tf)
    fw = min(2.6, w * 0.4)
    prisma(PRED, [(-fw / 2, h), (fw / 2, h), (fw / 2 - 0.25, h + 0.55), (-fw / 2 + 0.25, h + 0.55)], zf - 0.15, zf + 0.05, cor, tf)
    box2(PRED, -fw / 2 + 0.15, h + 0.55, zf - 0.17, fw / 2 - 0.15, h + 0.65, zf + 0.09, clara, tf)
    lathe(PRED, [(0.22, 0.0), (0.22, 0.06)], clara, 10, comp(tf, lambda p: (p[0], h + 0.27 + p[2], zf + 0.05 + p[1])), tampa=True)
    for s in (-1, 1):  # pilastras nas pontas
        box2(PRED, s * w / 2, 3.6, zf - 0.02, s * (w / 2 - 0.24), h, zf + 0.1, clara, tf)
    parapeito(w, d, h, cor, tf, alt=0.15)
    if random.random() < 0.6:  # caixa-d'água azul
        cx, cz = random.uniform(-w / 2 + 1.2, w / 2 - 1.2), random.uniform(-d / 2 + 1.5, -0.5)
        azul = C(0x3d7fb8)
        lathe(PRED, [(0.55, 0), (0.62, 0.15), (0.62, 0.85), (0.66, 0.9), (0.4, 1.05), (0.0, 1.1)], azul, 12, comp(tf, TF(cx, h, cz)))
    janelas_laterais(L, tf, 3.6, 3.6, n - 1, mold, vid)
    box2(COLI, -w / 2, 0, -d / 2, w / 2, h + 0.3, d / 2, BRANCO, tf)


def telhado(w, d, h, rh, tf, cor, g=None):
    g = g or PRED
    ov_f, ov_s = 0.5, 0.3
    ze, ye, yr = d / 2 + ov_f, h - 0.15, h + rh
    nrm_len = math.hypot(ze, yr - ye)
    linhas = max(5, int(nrm_len / 0.34))
    nx = max(4, int((w + 2 * ov_s) / 0.3))
    for lado in (1, -1):
        ny, nz = ze / nrm_len, lado * (yr - ye) / nrm_len
        for i in range(linhas):
            t0, t1 = i / linhas, (i + 1) / linhas
            z0, z1 = lado * ze * (1 - t0), lado * ze * (1 - t1)
            y0, y1 = ye + (yr - ye) * t0 + 0.05, ye + (yr - ye) * t1
            c = esc(cor, random.uniform(0.84, 1.08))
            verts, faces = [], []
            for j in range(nx + 1):
                x = -w / 2 - ov_s + (w + 2 * ov_s) * j / nx
                o = 0.04 if j % 2 == 0 else -0.01
                verts.append(tf((x, y0 + ny * o, z0 + nz * o)))
                verts.append(tf((x, y1 + ny * o, z1 + nz * o)))
            for j in range(nx):
                a = 2 * j
                faces.append((a, a + 2, a + 3, a + 1) if lado > 0 else (a + 1, a + 3, a + 2, a))
            g.add(verts, faces, [c] * len(verts))
    box2(g, -w / 2 - ov_s, yr - 0.03, -0.14, w / 2 + ov_s, yr + 0.1, 0.14, esc(cor, 0.78), tf)
    return yr


def casa(L):
    w, d, h, n = L['w'], L['d'], L['h'], L['andares']
    tf = TF(L['cx'], 0, L['cz'], L['rot'])
    zf = d / 2
    cor = var(C(L['cor']), 0.05)
    box2(PRED, -w / 2, 0, -d / 2, w / 2, h, d / 2, cor, tf)
    box2(PRED, -w / 2 - 0.02, 0, zf, w / 2 + 0.02, 0.75, zf + 0.04, esc(cor, 0.72), tf)
    for s in (-1, 1):  # cunhais
        box2(PRED, min(s * w / 2, s * (w / 2 - 0.28)), 0, zf - 0.01, max(s * w / 2, s * (w / 2 - 0.28)), h, zf + 0.06, BRANCO, tf)
    cols = max(2, round((w - 0.6) / 2.2))
    passo = (w - 0.6) / cols
    porta_i = random.randint(0, cols - 1)
    vz = C(random.choice(VENEZ))
    mold = BRANCO
    vid = C(random.choice(VIDROS))
    madeira = var(C(random.choice([0x7a4b2a, 0x5a3a22, 0x8a5a32, 0x2e5d4b])), 0.05)
    for k in range(n):
        y = 3.0 * k
        if k:
            box2(PRED, -w / 2 - 0.03, y - 0.08, zf - 0.02, w / 2 + 0.03, y + 0.08, zf + 0.1, BRANCO, tf)
        for i in range(cols):
            x = -w / 2 + 0.3 + passo * (i + 0.5)
            if k == 0 and i == porta_i:
                porta(x, 0.0, 1.05, 2.35, zf, tf, mold, madeira)
            elif k == 1 and i == porta_i and random.random() < 0.6:
                janela(x, y + 0.25, 0.95, 2.2, zf, tf, mold, vid)
                sacada(x, y + 0.1, 1.4, zf, tf, 'ferro', BRANCO)
            else:
                janela(x, y + 0.95, 0.95, 1.45, zf, tf, mold, vid, BRANCO, venez=vz)
    box2(PRED, -w / 2 - 0.12, h - 0.28, zf - 0.02, w / 2 + 0.12, h, zf + 0.16, BRANCO, tf)
    rh = random.uniform(1.4, 2.0)
    telha = var(C(random.choice([0xb5583a, 0xa94f34, 0xc0673f, 0x9c4a30])), 0.04)
    yr = telhado(w, d, h, rh, tf, telha)
    prisma(PRED, [(-d / 2, h), (d / 2, h), (0, yr - 0.1)], -w / 2, w / 2, cor, tf, eixo='x')
    box2(COLI, -w / 2, 0, -d / 2, w / 2, h, d / 2, BRANCO, tf)
    prisma(COLI, [(-d / 2 - 0.5, h - 0.15), (d / 2 + 0.5, h - 0.15), (0, yr)], -w / 2 - 0.3, w / 2 + 0.3, BRANCO, tf, eixo='x')


def gerar_quadras():
    global PRED
    lados = [
        (-46, 46, lambda a, d: (a, -(30.5 + d / 2)), 0.0),
        (-46, 46, lambda a, d: (a, 30.5 + d / 2), math.pi),
        (-29, 29, lambda a, d: (-(30.5 + d / 2), a), math.pi / 2),
        (-29, 29, lambda a, d: (30.5 + d / 2, a), -math.pi / 2),
    ]
    todos = []
    for li, (de, ate, pos, rot) in enumerate(lados):
        a, fila = de, []
        while a < ate:
            w = random.uniform(6.5, 10.5)
            r = random.random()
            if r < 0.3:
                tipo, d, n = 'casa', random.uniform(8, 10), random.choice([1, 2, 2])
                h = 3.6 if n == 1 else 6.4
            elif r < 0.55:
                tipo, d, n = 'sobrado', random.uniform(9, 11), random.choice([2, 3])
                h = 3.6 * n + 0.9
            else:
                tipo, d, n = 'predio', random.uniform(10, 14), random.randint(4, 9)
                h = 4.2 + 3.0 * (n - 1) + 1.0
            cx, cz = pos(a + w / 2, d)
            fila.append(dict(tipo=tipo, w=w, d=d, h=h, andares=n, cx=cx, cz=cz, rot=rot, cor=random.choice(FACH)))
            a += w + 0.25
        inv = rot in (math.pi, math.pi / 2)
        for i, L in enumerate(fila):
            prev = fila[i - 1]['h'] if i > 0 else 0
            nxt = fila[i + 1]['h'] if i + 1 < len(fila) else 0
            L['viz'] = (nxt, prev) if inv else (prev, nxt)
        PRED = list(LADOS_PRED.values())[li]
        for L in fila:
            {'casa': casa, 'sobrado': sobrado, 'predio': predio}[L['tipo']](L)
        todos += fila
    return todos


# =====================================================================
# ÁRVORES
# =====================================================================
def copa_malha(partes, voxel, faces, seed, lumps=6, amp=0.14, freq=1.2, lump_r=(0.38, 0.55)):
    """União de esferas (com tufos menores na superfície), remalhada, reduzida e amassada com ruído.
    partes: [(x, y, z, r)] no jogo. Devolve vértices (jogo), faces e normais (jogo)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    esf = []
    for (cx, cy, cz, r) in partes:
        esf.append((cx, cy, cz, r, r * 0.9, r))
        for _ in range(lumps):
            d = Vector((rnd.uniform(-1, 1), rnd.uniform(-0.35, 1), rnd.uniform(-1, 1))).normalized()
            rr = r * rnd.uniform(*lump_r)
            esf.append((cx + d.x * r * 0.8, cy + d.y * r * 0.72, cz + d.z * r * 0.8, rr, rr * 0.9, rr))
    for (cx, cy, cz, rx, ry, rz) in esf:
        m = Matrix.LocRotScale(Vector((cx, -cz, cy)), Quaternion(), Vector((rx, rz, ry)))
        bmesh.ops.create_uvsphere(bm, u_segments=18, v_segments=10, radius=1.0, matrix=m)
    me = bpy.data.meshes.new('tmp_copa')
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new('tmp_copa', me)
    colecao().objects.link(ob)
    md = ob.modifiers.new('r', 'REMESH')
    md.mode = 'VOXEL'
    md.voxel_size = voxel
    sm = ob.modifiers.new('s', 'SMOOTH')
    sm.factor, sm.iterations = 0.7, 6
    dg = bpy.context.evaluated_depsgraph_get()
    bpy.context.view_layer.update()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    ob.data = me2
    if len(me2.polygons) > faces:
        dm = ob.modifiers.new('d', 'DECIMATE')
        dm.ratio = faces / len(me2.polygons)
        bpy.context.view_layer.update()
        me3 = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        ob.modifiers.clear()
        ob.data = me3
    me = ob.data
    off = Vector((seed * 1.7, seed * 0.3, seed * 2.9))
    for v in me.vertices:
        v.co += v.normal * amp * noise.noise(v.co * freq + off)
    me.update()
    verts = [(v.co.x, v.co.z, -v.co.y) for v in me.vertices]
    norms = [(v.normal.x, v.normal.z, -v.normal.y) for v in me.vertices]
    fcs = [tuple(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(ob)
    return verts, fcs, norms


def pinta_copa(p, n, pal, seed):
    up = 0.5 + 0.5 * n[1]
    k = noise.noise(Vector(p) * 0.8 + Vector((seed, seed * 0.7, seed * 1.3)))
    c = mix(pal['escuro'], pal['medio'], sst(0.15, 0.65, up + 0.3 * k))
    c = mix(c, pal['claro'], sst(0.74, 1.0, up + 0.22 * k))
    if 'flor' in pal:
        f = sst(-0.25, 0.2, noise.noise(Vector(p) * 1.8 + Vector((3.1, seed, 7.7)))) * pal['flor_qtd']
        c = mix(c, mix(pal['flor'], pal['flor2'], sst(0.45, 1.0, up + 0.2 * k)), f)
    return c


PAL = {
    'verde': dict(escuro=C(0x2c5f2a), medio=C(0x3f8a36), claro=C(0x7cb850)),
    'sibipiruna': dict(escuro=C(0x2b6129), medio=C(0x48943a), claro=C(0x92c45a), flor=C(0xe8c22a), flor2=C(0xf6d65a), flor_qtd=0.18),
    'pitangueira': dict(escuro=C(0x1d451d), medio=C(0x2d6528), claro=C(0x4f8d3a)),
    'ipe_amarelo': dict(escuro=C(0x5d7a26), medio=C(0x8a9a2c), claro=C(0xa9b24a), flor=C(0xefb413), flor2=C(0xffdc45), flor_qtd=0.95),
    'ipe_rosa': dict(escuro=C(0x6a7a3a), medio=C(0x8a8a4a), claro=C(0xa0a060), flor=C(0xd85fa3), flor2=C(0xf5a8d0), flor_qtd=0.95),
    'calcada': dict(escuro=C(0x2f5e2b), medio=C(0x47873a), claro=C(0x86b955)),
}


def copa(g, partes, pal, voxel, faces, seed, **kw):
    v, f, n = copa_malha(partes, voxel, faces, seed, **kw)
    g.add(v, f, [pinta_copa(p, nn, PAL[pal], seed) for p, nn in zip(v, n)])


def galho(g, p0, p1, r0, r1, cor, seg=6, curva=0.0):
    p0, p1 = Vector(p0), Vector(p1)
    mid = p0.lerp(p1, 0.5) + Vector((0, curva, 0))
    tubo(g, [p0, p0.lerp(mid, 0.6), mid, mid.lerp(p1, 0.5), p1], [r0, r0 * 0.9 + r1 * 0.1, (r0 + r1) / 2, r1 * 1.1, r1],
         lambda i: var(cor, 0.06), seg)


def tronco(g, x, y0, z, h, r, cor, inclina=(0.0, 0.0)):
    lathe(g, [(r * 1.55, -0.05), (r * 1.25, 0.12), (r * 1.05, 0.35)], esc(cor, 0.9), 8, TF(x, y0, z))
    pts = [Vector((x + inclina[0] * t * t, y0 + h * t, z + inclina[1] * t * t)) for t in (0.0, 0.3, 0.6, 1.0)]
    tubo(g, pts, [r, r * 0.88, r * 0.76, r * 0.65], lambda i: var(cor, 0.05), 8)


def flores_chao(g, x, z, raio, cores, n=220, seed=1):
    rnd = random.Random(seed)
    for _ in range(n):
        a, d = rnd.uniform(0, 2 * math.pi), raio * math.sqrt(rnd.random())
        px, pz = x + math.cos(a) * d, z + math.sin(a) * d
        if not (1.75 < abs(px) < 16.95 and 1.75 < abs(pz) < 16.95 and math.hypot(px, pz) > 6.75):
            continue  # só na grama do canteiro
        y = groundY(px, pz) + 0.012
        s = rnd.uniform(0.05, 0.09)
        t = rnd.uniform(0, 2 * math.pi)
        c = C(rnd.choice(cores))
        g.add([(px + math.cos(t) * s, y, pz + math.sin(t) * s), (px + math.cos(t + 2.2) * s, y, pz + math.sin(t + 2.2) * s),
               (px + math.cos(t + 4.1) * s, y, pz + math.sin(t + 4.1) * s)], [(0, 2, 1)], [c] * 3)


def arvore(x, z, h, r, partes_rel, pal, seed, faces=1300, voxel=0.16, cor_tronco=0x6b4a33, gcopa=None, **kw):
    y0 = groundY(x, z)
    ct = C(cor_tronco)
    tronco(TRONCO, x, y0, z, h, r, ct)
    rnd = random.Random(seed)
    topo = Vector((x, y0 + h, z))
    for (bx, by, bz, br) in partes_rel:  # galhos do alto do tronco até cada tufo
        alvo = Vector((x + bx * 0.85, y0 + by - br * 0.35, z + bz * 0.85))
        base = Vector((x, y0 + h * rnd.uniform(0.72, 0.95), z))
        galho(TRONCO, base, alvo, r * 0.5, r * 0.18, ct)
    partes = [(x + bx, y0 + by, z + bz, br) for (bx, by, bz, br) in partes_rel]
    copa(gcopa or COPA, partes, pal, voxel, faces, seed, **kw)


TREE, NEST_TREE_H = (9.0, -7.0), 5.4
DUET_A, DUET_B = Vector((9, 3.0, -7)), Vector((5.6, 3.3, -7.7))


def arvore_ninho():
    x, z = TREE
    y0 = groundY(x, z)
    ct = C(0x6b4423)
    B = lambda a, b, c: Vector((a, y0 + b, c))
    tronco(ARV_N, x, y0, z, NEST_TREE_H, 0.42, ct)
    # galhos com as mesmas medidas do jogo (o ninho e o dueto ficam neles)
    for p0, p1, r in [(B(9, 3.3, -7), B(8.05, 4.04, -6.15), 0.12), (B(8.05, 4.04, -6.15), B(7.2, 4.6, -6.6), 0.08),
                      (B(8.05, 4.04, -6.15), B(8.75, 4.8, -6.2), 0.08), (DUET_A, DUET_B, 0.1),
                      (DUET_B, DUET_B + Vector((-0.7, 0.45, -0.3)), 0.05),
                      (B(9, 5.1, -7), B(10.3, 6.3, -6.2), 0.12), (B(9, 4.8, -7), B(7.9, 6.0, -7.8), 0.12)]:
        tubo(ARV_N, [p0, p0.lerp(p1, 0.5), p1], [r, r * 0.85, r * 0.7], lambda i: var(ct, 0.05), 8)
    for p1 in (B(10.4, 6.9, -6.4), B(7.8, 6.9, -8.0), B(9.3, 7.9, -7.9), B(8.4, 7.1, -5.8), B(9.9, 6.6, -8.3)):
        galho(ARV_N, B(9, NEST_TREE_H - 0.2, -7), p1, 0.2, 0.07, ct, 6)
    blobs = [[0, 7.2, 0, 2.3], [1.5, 6.6, 0.8, 1.7], [-1.3, 6.6, -1.0, 1.8], [0.4, 8.0, -0.9, 1.6], [0.9, 6.5, -1.4, 1.5], [-0.6, 6.9, 1.2, 1.5]]
    copa(COPA_N, [(x + a, y0 + b, z + c, r) for a, b, c, r in blobs], 'sibipiruna', 0.17, 2600, 11, lumps=7)
    # tufo de folhas na ponta do galho do dueto
    t = DUET_B + Vector((-0.8, 0.6, -0.35))
    copa(COPA, [(t.x, t.y, t.z, 0.45), (t.x + 0.25, t.y - 0.1, t.z + 0.2, 0.3)], 'sibipiruna', 0.08, 260, 5, lumps=4, amp=0.05)


def pitangueira():
    x, z = -8.0, 8.0
    y0 = groundY(x, z)
    ct = C(0x5b4636)
    for dx, dz in ((0.0, 0.0), (0.25, -0.15), (-0.2, 0.2)):
        galho(TRONCO, (x + dx * 0.3, y0, z + dz * 0.3), (x + dx * 2.2, y0 + 1.7, z + dz * 2.2), 0.11, 0.06, ct, 6)
    blobs = [[0, 2.2, 0, 1.12], [0.8, 1.9, 0.3, 0.85], [-0.7, 2.0, -0.2, 0.9], [0.1, 2.9, 0, 0.8]]
    copa(COPA, [(x + a, y0 + b, z + c, r) for a, b, c, r in blobs], 'pitangueira', 0.1, 1000, 21, lumps=8, amp=0.06,
         lump_r=(0.3, 0.42))


def arvores():
    arvore_ninho()
    pitangueira()
    padrao = lambda h: [[0, h + 0.9, 0, 2.2], [1.3, h + 0.4, 0.4, 1.6], [-1.2, h + 0.5, -0.3, 1.7], [0.2, h + 1.8, -0.6, 1.6], [-0.4, h + 0.4, 1.2, 1.5]]
    arvore(-15, -2.5, 3.8, 0.3, padrao(3.8), 'ipe_amarelo', 31, 1500, 0.16, 0x6e5a48, lumps=9, amp=0.2, lump_r=(0.3, 0.5))
    flores_chao(MOV, -15, -2.5, 3.0, [0xf2c12e, 0xffd84a, 0xe6a817], 520, 3)
    arvore(14, 12, 4.0, 0.3, padrao(4.0), 'ipe_rosa', 32, 1500, 0.16, 0x6e5a48, lumps=9, amp=0.2, lump_r=(0.3, 0.5))
    flores_chao(MOV, 14, 12, 3.0, [0xe58cc0, 0xf5a8d0, 0xd06aa0], 420, 4)
    for (x, z, h, sd) in ((14.5, -15, 4.6, 33), (3.5, 14.5, 4.2, 34), (-3.5, -14.5, 3.6, 35)):
        arvore(x, z, h, 0.3, padrao(h), 'verde', sd, 1300)
    # árvores das calçadas, com canteiro
    pontos = [(x, -28.6) for x in (-38, -24, -10, 10, 24, 38)] + [(x, 28.6) for x in (-38, -24, -10, 10, 24, 38)] + \
             [(-28.6, z) for z in (-20, -6, 8, 20)] + [(28.6, z) for z in (-20, 6, 20)]
    for i, (x, z) in enumerate(pontos):
        h = random.uniform(2.8, 3.6)
        partes = [[0, h + 0.8, 0, 1.5], [0.8, h + 0.4, 0.3, 1.1], [-0.7, h + 0.5, -0.3, 1.15], [0.1, h + 1.4, -0.3, 1.05]]
        arvore(x, z, h, 0.17, partes, 'calcada', 100 + i, 520, 0.2, 0x5f4a38, gcopa=COPA_RUA, lumps=4, amp=0.12)
        y0 = groundY(x, z)
        box2(MOV, x - 0.6, y0 - 0.02, z - 0.6, x + 0.6, y0 + 0.04, z + 0.6, C(0x5a4632), )
        for s in (-1, 1):
            box2(MOV, x - 0.66, y0 - 0.02, z + s * 0.6 - 0.06, x + 0.66, y0 + 0.08, z + s * 0.6 + 0.06, C(0xbdb7ab))
            box2(MOV, x + s * 0.6 - 0.06, y0 - 0.02, z - 0.6, x + s * 0.6 + 0.06, y0 + 0.08, z + 0.6, C(0xbdb7ab))


# =====================================================================
# MÓVEIS DA PRAÇA E DA RUA
# =====================================================================
LAMPS = [(5.5, -3.5), (-5.5, 3.5), (5.5, 3.5), (-5.5, -3.5), (13, 1.2), (-13, -1.2), (1.2, 13), (-1.2, -13)]


def poste_colonial(x, z):
    y0 = groundY(x, z)
    tf = TF(x, y0, z)
    ferro = C(0x2f4f3f)
    lathe(MOV, [(0.21, 0.0), (0.21, 0.1), (0.17, 0.14), (0.15, 0.45), (0.11, 0.55), (0.085, 0.72), (0.07, 0.9),
                (0.062, 3.62), (0.085, 3.66), (0.085, 3.74), (0.13, 3.8)], ferro, 8, tf)
    lathe(LUZ, [(0.12, 3.8), (0.2, 4.05), (0.2, 4.16), (0.15, 4.28)], C(0xfff1c8), 6, tf, fase=math.pi / 6)
    for k in range(6):
        a = 2 * math.pi * k / 6 + math.pi / 6
        tubo(MOV, [(0.125 * math.cos(a), 3.8, 0.125 * math.sin(a)), (0.205 * math.cos(a), 4.05, 0.205 * math.sin(a)),
                   (0.205 * math.cos(a), 4.16, 0.205 * math.sin(a)), (0.155 * math.cos(a), 4.28, 0.155 * math.sin(a))],
             [0.012] * 4, ferro, 4, tf, tampas=False)
    lathe(MOV, [(0.15, 4.27), (0.25, 4.3), (0.25, 4.33), (0.13, 4.42), (0.06, 4.47), (0.06, 4.48)], ferro, 6, tf,
          tampa=True, fase=math.pi / 6)


BANCOS = []
for _i in range(4):
    for _off in (-0.55, 0.55):
        _a = _i * math.pi / 2 + math.pi / 4 + _off
        BANCOS.append((math.cos(_a) * 6.05, math.sin(_a) * 6.05))


def banco(x, z):
    y0 = groundY(x, z)
    tf = TF(x, y0, z, math.atan2(-x, -z))
    madeira, ferro = C(0x9b6a3c), C(0x2f4f3f)
    for zc in (-0.18, -0.06, 0.06, 0.18):
        box2(MOV, -0.9, 0.41, zc - 0.05, 0.9, 0.49, zc + 0.05, var(madeira, 0.08), tf)
    for ya, yb in ((0.56, 0.66), (0.70, 0.80), (0.84, 0.94)):
        box2(MOV, -0.9, ya, -0.27, 0.9, yb, -0.21, var(madeira, 0.08), tf)
    for xs in (-0.75, 0.75):
        box2(MOV, xs - 0.03, 0, 0.16, xs + 0.03, 0.41, 0.22, ferro, tf)
        box2(MOV, xs - 0.03, 0, -0.33, xs + 0.03, 0.93, -0.27, ferro, tf)
        box2(MOV, xs - 0.03, 0.35, -0.3, xs + 0.03, 0.41, 0.24, ferro, tf)
        box2(MOV, xs - 0.035, 0.64, -0.3, xs + 0.035, 0.69, 0.26, ferro, tf)
        box2(MOV, xs - 0.025, 0.41, 0.2, xs + 0.025, 0.66, 0.24, ferro, tf)
        box2(MOV, xs - 0.04, 0, 0.12, xs + 0.04, 0.04, 0.26, ferro, tf)
        box2(MOV, xs - 0.04, 0, -0.36, xs + 0.04, 0.04, -0.24, ferro, tf)


LIXEIRAS = [(1.25, 9.5), (9.5, 1.25), (-9.5, -1.25), (-12.4, 12.8)]


def lixeira(x, z):
    y0 = groundY(x, z)
    tf = TF(x, y0, z)
    lar, esc_l = C(0xe8742a), C(0xa04a16)
    lathe(MOV, [(0.23, 0.0), (0.25, 0.04), (0.27, 0.1), (0.31, 0.74), (0.33, 0.76), (0.33, 0.82), (0.29, 0.82), (0.29, 0.76), (0.27, 0.58)],
          lambda i, r, y: esc_l if y > 0.75 or y < 0.05 else lar, 12, tf)
    lathe(MOV, [(0.27, 0.58), (0.0, 0.58)], C(0x3a2a20), 12, tf)
    lathe(MOV, [(0.305, 0.36), (0.315, 0.36), (0.32, 0.46), (0.31, 0.46)], C(0xf3efe6), 12, tf)


def banca():
    x, z = -14.5, 14.5
    y0 = groundY(x, z)
    tf = TF(x, y0, z, math.atan2(-x, -z))
    verde, verde2 = C(0x2e7d5b), C(0x23664a)
    box2(MOV, -1.45, 0, -1.05, 1.45, 0.1, 1.05, C(0x55595e), tf)
    box2(MOV, -1.4, 0.1, -1.0, 1.4, 2.2, 1.0, verde, tf)
    box2(MOV, -1.55, 2.2, -1.15, 1.55, 2.3, 1.15, verde2, tf)  # teto: topo em 2,3 m
    for k in range(9):  # nervuras laterais e de trás
        t = -0.85 + 1.7 * k / 8
        for s in (-1, 1):
            box2(MOV, s * 1.4 - 0.02, 0.15, t - 0.03, s * 1.4 + 0.02, 2.15, t + 0.03, verde2, tf)
        box2(MOV, t * 1.5 - 0.03, 0.15, -1.02, t * 1.5 + 0.03, 2.15, -0.98, verde2, tf)
    box2(MOV, -1.4, 0.85, 1.0, 1.4, 0.93, 1.3, C(0x55595e), tf)  # balcão
    capas = [0xe0452b, 0x4aa3df, 0xffffff, 0xf2c12e, 0x8bc34a, 0xff8c42, 0x9b59b6, 0x1abc9c, 0xe67e22, 0xecf0f1, 0xc0392b, 0x2980b9]
    for row, yy in enumerate((1.05, 1.5, 1.95 - 0.38)):
        for i in range(6):
            xx = -1.15 + i * 0.46
            if row == 2 and i in (0, 5):
                continue
            c = C(capas[(i * 3 + row * 5) % len(capas)])
            box2(MOV, xx - 0.17, yy, 1.0, xx + 0.17, yy + 0.4, 1.035, c, tf)
            box2(MOV, xx - 0.12, yy + 0.24, 1.035, xx + 0.12, yy + 0.33, 1.04, esc(c, 0.55) if sum(c) > 1.5 else BRANCO, tf)
    box2(MOV, -1.4, 1.98, 1.0, 1.4, 2.2, 1.05, C(0xffd21f), tf)
    for i in range(5):  # "BANCA" em blocos
        xx = -0.9 + i * 0.45
        box2(MOV, xx - 0.13, 2.02, 1.05, xx + 0.13, 2.16, 1.07, C(0xd8402a), tf)
    toldo_b = [(0xffd21f, 0xffffff)]
    # toldo na frente (abaixo da beira do teto)
    n = 9
    for i in range(n):
        xa, xb = -1.5 + 3.0 * i / n, -1.5 + 3.0 * (i + 1) / n
        c = C(toldo_b[0][i % 2])
        quad(MOV, (xa, 2.24, 1.16), (xb, 2.24, 1.16), (xb, 1.94, 2.0), (xa, 1.94, 2.0), c, tf)
        quad(MOV, (xa, 1.94, 2.0), (xb, 1.94, 2.0), (xb, 1.76, 2.0), (xa, 1.76, 2.0), c, tf)
    for s in (-1, 1):  # jornais pendurados nas laterais
        for k in range(3):
            c = C([0xf3efe6, 0xe0e0d8, 0xf6e7c1][k])
            box2(MOV, s * 1.42, 0.9 + k * 0.42, 0.2 - k * 0.15, s * 1.45, 1.25 + k * 0.42, 0.6 - k * 0.15, c, tf)


def coreto():
    x, z = -9.5, -9.5
    y0 = groundY(x, z)
    rot = math.atan2(-x, -z)
    tf = TF(x, y0, z, rot)
    creme, branco, telha, ouro = C(0xece5d3), C(0xfbfaf5), C(0xc0503a), C(0xf2c12e)
    f8 = math.pi / 8
    lathe(MOV, [(2.72, 0.0), (2.72, 0.1), (2.62, 0.14), (2.56, 0.58), (2.64, 0.62), (2.64, 0.7), (0.0, 0.7)],
          lambda i, r, y: esc(creme, 0.85) if y < 0.12 else creme, 8, tf, fase=f8)
    for k, (ya, yb, za) in enumerate(((0.0, 0.24, 3.35), (0.24, 0.47, 3.0), (0.47, 0.7, 2.7))):
        box2(MOV, -0.8, ya, 2.4, 0.8, yb, za, esc(creme, 0.95 - 0.03 * k), tf)
    cols = []
    for i in range(8):
        a = i / 8 * 2 * math.pi + f8
        cx, cz = math.cos(a) * 2.25, math.sin(a) * 2.25
        cols.append((cx, cz))
        lathe(MOV, [(0.13, 0.7), (0.13, 0.82), (0.09, 0.9), (0.075, 1.0), (0.07, 3.0), (0.1, 3.08), (0.14, 3.16)], branco, 8,
              comp(tf, TF(cx, 0, cz)))
    # guarda-corpo entre as colunas (menos na entrada, virada para +z local)
    for i in range(8):
        (ax, az), (bx, bz) = cols[i], cols[(i + 1) % 8]
        if (az + bz) / 2 > 1.6 and abs((ax + bx) / 2) < 1.0:
            continue
        viga(MOV, (ax, 1.62, az), (bx, 1.62, bz), 0.08, 0.06, branco, tf)
        viga(MOV, (ax, 0.82, az), (bx, 0.82, bz), 0.06, 0.05, branco, tf)
        for j in range(1, 8):
            t = j / 8
            px, pz = ax + (bx - ax) * t, az + (bz - az) * t
            lathe(MOV, [(0.025, 0.84), (0.045, 1.0), (0.03, 1.2), (0.045, 1.4), (0.025, 1.6)], branco, 4, comp(tf, TF(px, 0, pz)))
    for i in range(8):  # friso sob o telhado
        (ax, az), (bx, bz) = cols[i], cols[(i + 1) % 8]
        viga(MOV, (ax, 3.18, az), (bx, 3.18, bz), 0.12, 0.14, branco, tf)
    lathe(MOV, [(3.08, 3.25), (3.04, 3.33), (1.2, 4.12), (0.18, 4.58), (0.0, 4.64)],
          lambda i, r, y: telha if i else esc(telha, 0.75), 8, tf, fase=f8)
    lathe(MOV, [(3.06, 3.24), (0.0, 3.62)], C(0xf6f1e4), 8, tf, fase=f8)
    for i in range(8):  # lambrequim: franja de dentes na beira do telhado
        a0, a1 = i / 8 * 2 * math.pi + f8, (i + 1) / 8 * 2 * math.pi + f8
        p0 = (math.cos(a0) * 3.07, math.sin(a0) * 3.07)
        p1 = (math.cos(a1) * 3.07, math.sin(a1) * 3.07)
        for j in range(8):
            t0, t1, tm = j / 8, (j + 1) / 8, (j + 0.5) / 8
            A = (p0[0] + (p1[0] - p0[0]) * t0, 3.26, p0[1] + (p1[1] - p0[1]) * t0)
            Bp = (p0[0] + (p1[0] - p0[0]) * t1, 3.26, p0[1] + (p1[1] - p0[1]) * t1)
            Mp = (p0[0] + (p1[0] - p0[0]) * tm, 3.08, p0[1] + (p1[1] - p0[1]) * tm)
            MOV.add([tf(A), tf(Bp), tf(Mp)], [(0, 1, 2)], [branco] * 3)
    lathe(MOV, [(0.14, 4.6), (0.17, 4.68), (0.1, 4.78), (0.05, 4.95), (0.0, 5.05)], ouro, 8, tf)


POSTES_X, ZP = [-35, -21, -7, 7, 21, 35], -20.2


def postes_e_fios():
    concreto, cinza = C(0x9b9690), C(0x7d7871)
    for x in POSTES_X:
        lathe(MOV, [(0.19, 0.0), (0.17, 0.4), (0.12, 7.95), (0.0, 8.05)], concreto, 6, TF(x, 0, ZP))
        box2(MOV, x - 0.08, 7.5, ZP - 0.85, x + 0.08, 7.64, ZP + 0.85, cinza)
        for dz in (-0.6, 0.6, 0.0):
            lathe(MOV, [(0.05, 7.64), (0.06, 7.68), (0.04, 7.72), (0.05, 7.76), (0.02, 7.8)], C(0xcfe3d6), 6, TF(x, 0, ZP + dz))
        # braço de iluminação pública virado para a rua
        tubo(MOV, [(x, 6.4, ZP), (x, 6.9, ZP - 0.6), (x, 7.0, ZP - 1.6)], [0.05, 0.045, 0.04], cinza, 6)
        box2(MOV, x - 0.14, 6.88, ZP - 1.95, x + 0.14, 7.02, ZP - 1.45, cinza)
        box2(LUZ, x - 0.11, 6.84, ZP - 1.9, x + 0.11, 6.88, ZP - 1.5, C(0xfff1c8))
    # transformador
    lathe(MOV, [(0.0, 5.3), (0.34, 5.3), (0.34, 6.25), (0.36, 6.3), (0.0, 6.42)], C(0x8a8f94), 10, TF(21, 0, ZP + 0.48))
    box2(MOV, 20.9, 5.6, ZP + 0.05, 21.1, 5.75, ZP + 0.2, C(0x55595e))
    # fios: curva de Bézier quadrática igual à do jogo (y 7,65 nos postes, 6,25 no ponto de controle)
    for i in range(len(POSTES_X) - 1):
        xa, xb = POSTES_X[i], POSTES_X[i + 1]
        for dz, y, sag, r in ((-0.6, 7.65, 1.4, 0.025), (0.6, 7.65, 1.4, 0.025), (0.0, 7.0, 0.9, 0.04)):
            pts = []
            for k in range(19):
                u = k / 18
                yy = y * (1 - u) ** 2 + 2 * u * (1 - u) * (y - sag) + y * u * u
                pts.append((xa + (xb - xa) * u, yy, ZP + dz))
            tubo(FIO, pts, [r] * len(pts), C(0x222222), 4, tampas=False)


CARROS = [(-8, 20.2, 0.0, 0xd8402a), (9, 20.2, 0.0, 0x2f6fb3), (-20.2, -9, math.pi / 2, 0xf2f2ee), (20.2, 8, math.pi / 2, 0xf2c12e),
          (20.2, -12, math.pi / 2, 0x3a3a3a), (-12, -22.8, 0.0, 0x3fae6a)]


def carro(x, z, rot, cor_h):
    tf = TF(x, 0, z, rot)
    cor = C(cor_h)
    escuro, cromo, pneu = C(0x2a2a2a), C(0xc9ccd0), C(0x1c1c1c)
    perfil = [(-2.05, 0.28), (2.05, 0.28), (2.08, 0.55), (2.0, 0.74), (1.1, 0.86), (-1.62, 0.88), (-2.02, 0.8), (-2.08, 0.55)]
    prisma(MOV, perfil, -0.9, 0.9, cor, tf, eixo='x')
    cabine = [(1.08, 0.86), (0.78, 1.4), (-1.22, 1.4), (-1.6, 0.88)]
    prisma(VIDRO, cabine, -0.79, 0.79, C(0x3d4f5f), tf, eixo='x')
    box2(MOV, -0.8, 1.4, -1.2, 0.8, 1.46, 0.8, cor, tf)  # teto: topo em 1,46 m
    for s in (-1, 1):  # colunas
        for (za, ya), (zb, yb) in (((1.08, 0.86), (0.78, 1.4)), ((-1.6, 0.88), (-1.22, 1.4))):
            tubo(MOV, [(s * 0.8, ya, za), (s * 0.8, yb, zb)], [0.045, 0.045], cor, 4, tf)
        box2(MOV, s * 0.8 - 0.04, 0.86, -0.25, s * 0.8 + 0.04, 1.4, -0.15, cor, tf)
        box2(MOV, s * 0.93 - 0.05, 1.0, 0.85, s * 0.93 + 0.05, 1.1, 1.0, cor, tf)  # retrovisor
        for zw in (1.3, -1.3):
            tubo(MOV, [(s * 0.7, 0.34, zw), (s * 0.95, 0.34, zw)], [0.34, 0.34], pneu, 12, tf)
            tubo(MOV, [(s * 0.94, 0.34, zw), (s * 0.97, 0.34, zw)], [0.19, 0.17], cromo, 10, tf)
    box2(MOV, -0.92, 0.28, 1.98, 0.92, 0.44, 2.12, escuro, tf)
    box2(MOV, -0.92, 0.28, -2.12, 0.92, 0.44, -1.98, escuro, tf)
    box2(MOV, -0.45, 0.5, 2.03, 0.45, 0.66, 2.09, escuro, tf)
    for s in (-1, 1):
        box2(LUZ, s * 0.66 - 0.17, 0.56, 2.02, s * 0.66 + 0.17, 0.68, 2.08, C(0xfff3c4), tf)
        box2(MOV, s * 0.68 - 0.15, 0.58, -2.09, s * 0.68 + 0.15, 0.7, -2.03, C(0xc0302a), tf)
    for zz in (2.12, -2.12):
        box2(MOV, -0.25, 0.32, zz - 0.02, 0.25, 0.44, zz + 0.02, C(0xf3f1ea), tf)


def chafariz():
    pedra, pedra2, azulejo = C(0xd3c9b5), C(0xbdb39f), C(0x5f9fc8)
    cor = lambda i, r, y: azulejo if r < 3.31 and y < 0.94 else (esc(pedra, 0.92) if y < 0.4 else pedra)
    lathe(CHAF, [(3.8, 0.2), (3.8, 0.32), (3.72, 0.38), (3.72, 0.84), (3.76, 0.87), (3.76, 0.92), (3.68, 0.95), (3.3, 0.95),
                 (3.28, 0.93), (3.28, 0.45)], cor, 48)
    lathe(CHAF, [(3.28, 0.45), (0.0, 0.45)], azulejo, 48)
    for k in range(16):  # pilastras na parede de fora
        a = 2 * math.pi * k / 16
        box(CHAF, (0, 0, 0), (0.24, 0.5, 0.08), pedra2, TF(math.cos(a) * 3.75, 0.62, math.sin(a) * 3.75, math.atan2(math.cos(a), math.sin(a))))
    lathe(CHAF, [(0.7, 0.45), (0.66, 0.62), (0.45, 0.7), (0.42, 0.92), (0.32, 1.02), (0.27, 1.5), (0.31, 1.92), (0.37, 2.0),
                 (0.3, 2.12), (0.22, 2.3), (0.3, 2.34), (0.7, 2.4), (0.98, 2.55), (1.02, 2.67), (0.95, 2.67), (0.9, 2.6)],
          lambda i, r, y: pedra if i % 3 else pedra2, 20)
    lathe(CHAF, [(0.9, 2.6), (0.0, 2.6)], C(0x4f9fd0), 20)
    lathe(CHAF, [(0.13, 2.6), (0.11, 2.72), (0.17, 2.78), (0.14, 2.86), (0.07, 2.93), (0.0, 2.97)], pedra2, 10)


def orelhao(x, z, rot):
    tf = TF(x, 0.14, z, rot)
    lar, dentro = C(0xf28c28), C(0xf6d9b0)
    tubo(MOV, [(0, 0, -0.05), (0, 1.95, -0.05)], [0.05, 0.05], C(0x8a8f94), 6, tf)
    rx, ry, rz, cy = 0.5, 0.62, 0.48, 1.72
    nu, nv = 14, 8
    verts, faces, cols = [], [], []
    for i in range(nv + 1):
        v = 0.15 + (math.pi * 0.62) * i / nv
        for j in range(nu + 1):
            u = math.pi * 0.28 + (2 * math.pi - 2 * math.pi * 0.28) * j / nu
            verts.append(tf((math.sin(v) * math.sin(u) * rx, cy + math.cos(v) * ry, math.sin(v) * math.cos(u) * rz)))
            cols.append(lar)
    for i in range(nv):
        for j in range(nu):
            a = i * (nu + 1) + j
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    MOV.add(verts, faces, cols)
    box2(MOV, -0.12, 1.35, -0.42, 0.12, 1.7, -0.32, C(0x2f6fb3), tf)
    box2(MOV, -0.05, 1.5, -0.33, 0.05, 1.62, -0.28, C(0x1c1c1c), tf)


def ponto_onibus(x, z, rot):
    tf = TF(x, 0.14, z, rot)
    metal, azul = C(0x5b6670), C(0x2f6fb3)
    for xs in (-1.4, 1.4):
        box2(MOV, xs - 0.05, 0, -0.55, xs + 0.05, 2.45, -0.45, metal, tf)
    box2(MOV, -1.6, 2.45, -0.75, 1.6, 2.55, 0.75, azul, tf)
    quad(VIDRO, (-1.35, 0.3, -0.5), (1.35, 0.3, -0.5), (1.35, 2.3, -0.5), (-1.35, 2.3, -0.5), C(0x9cc6cf), tf)
    box2(MOV, -1.2, 0.42, -0.45, 1.2, 0.48, -0.1, C(0x9b6a3c), tf)
    box2(MOV, -1.1, 0, -0.35, -1.0, 0.42, -0.25, metal, tf)
    box2(MOV, 1.0, 0, -0.35, 1.1, 0.42, -0.25, metal, tf)
    tubo(MOV, [(2.0, 0, 0.3), (2.0, 2.6, 0.3)], [0.04, 0.04], metal, 6, tf)
    box2(MOV, 1.75, 2.2, 0.27, 2.25, 2.7, 0.33, azul, tf)
    box2(MOV, 1.82, 2.27, 0.33, 2.18, 2.63, 0.34, BRANCO, tf)


def placa_rua(x, z):
    tf = TF(x, groundY(x, z), z)
    tubo(MOV, [(0, 0, 0), (0, 2.7, 0)], [0.04, 0.035], C(0x5b6670), 6, tf)
    azul = C(0x1f4f9a)
    for rot in (0.0, math.pi / 2):
        t2 = comp(tf, TF(0, 0, 0, rot))
        box2(MOV, -0.05, 2.45, -0.02, 0.75, 2.68, 0.02, azul, t2)
        box2(MOV, 0.0, 2.48, 0.02, 0.7, 2.65, 0.025, BRANCO, t2)
        box2(MOV, 0.06, 2.51, 0.025, 0.64, 2.62, 0.03, azul, t2)


def hidrante(x, z):
    tf = TF(x, 0.14, z)
    lathe(MOV, [(0.14, 0.0), (0.14, 0.05), (0.1, 0.08), (0.1, 0.5), (0.13, 0.53), (0.11, 0.6), (0.06, 0.66), (0.0, 0.68)],
          C(0xd8402a), 10, tf)
    tubo(MOV, [(-0.17, 0.38, 0), (0.17, 0.38, 0)], [0.045, 0.045], C(0xf2c12e), 6, tf)


def meios_fios():
    conc = C(0xc8c3b8)
    for s in (-1, 1):  # borda da praça
        box2(MOV, -18.62, 0.0, s * 18.5 - 0.13, 18.62, 0.17, s * 18.5 + 0.13, conc)
        box2(MOV, s * 18.5 - 0.13, 0.0, -18.62, s * 18.5 + 0.13, 0.17, 18.62, conc)
        box2(MOV, -30.5, 0.0, s * 26.5 - 0.12, 30.5, 0.16, s * 26.5 + 0.12, conc)  # calçadas de fora
        box2(MOV, s * 26.5 - 0.12, 0.0, -26.5, s * 26.5 + 0.12, 0.16, 26.5, conc)
    for sx in (-1, 1):  # canteiros de grama
        for sz in (-1, 1):
            box2(MOV, sx * 1.65, 0.13, sz * 17.05 - 0.06, sx * 17.05, 0.26, sz * 17.05 + 0.06, conc)
            box2(MOV, sx * 17.05 - 0.06, 0.13, sz * 1.65, sx * 17.05 + 0.06, 0.26, sz * 17.05, conc)
            zi = math.sqrt(6.6 ** 2 - 1.65 ** 2)
            box2(MOV, sx * 1.65 - 0.06, 0.13, sz * zi, sx * 1.65 + 0.06, 0.26, sz * 17.05, conc)
            box2(MOV, sx * zi, 0.13, sz * 1.65 - 0.06, sx * 17.05, 0.26, sz * 1.65 + 0.06, conc)
    lathe(MOV, [(6.66, 0.17), (6.66, 0.27), (6.54, 0.27), (6.54, 0.2)], conc, 72)


def moveis():
    for x, z in LAMPS:
        poste_colonial(x, z)
    for x, z in BANCOS:
        banco(x, z)
    for x, z in LIXEIRAS:
        lixeira(x, z)
    banca()
    coreto()
    postes_e_fios()
    for c in CARROS:
        carro(*c)
    chafariz()
    orelhao(-27.9, 14.5, math.pi / 2)
    orelhao(15.0, 27.9, math.pi)
    ponto_onibus(28.0, -9.0, -math.pi / 2)
    for sx in (-1, 1):
        for sz in (-1, 1):
            placa_rua(sx * 18.15, sz * 18.15)
    hidrante(-27.0, -12.0)
    hidrante(27.0, 13.5)
    meios_fios()


# =====================================================================
# CONTEXTO (só para as prévias; o chão do jogo continua no código)
# =====================================================================
def contexto():
    box2(CTX, -70, -0.02, -70, 70, 0.0, 70, C(0x5d6166))
    for s in (-1, 1):
        box2(CTX, -30.5, 0, s * 28.5 - 2, 30.5, 0.14, s * 28.5 + 2, C(0xbdb7ab))
        box2(CTX, s * 28.5 - 2, 0, -26.5, s * 28.5 + 2, 0.14, 26.5, C(0xbdb7ab))
    box2(CTX, -18.5, 0, -18.5, 18.5, 0.15, 18.5, C(0xd9d1c0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            box2(CTX, sx * 1.65, 0.15, sz * 1.65, sx * 17.05, 0.21, sz * 17.05, C(0x6bad4f))
    lathe(CTX, [(6.6, 0.15), (6.6, 0.23), (0.0, 0.23)], C(0xefe9dc), 48)
    lathe(CTX, [(3.3, 0.8), (0.0, 0.8)], C(0x3f9fd0), 32)


# =====================================================================
gerar_quadras()
arvores()
moveis()
contexto()

saidas = []
for geo, nome, mat in tuple((g, n, 'cenario') for n, g in LADOS_PRED.items()) + ((VIDRO, 'vidros', 'vidro'), (LUZ, 'luzes', 'luz'), (FIO, 'fios', 'fio'),
                       (MOV, 'moveis', 'cenario'), (CHAF, 'chafariz', 'cenario'), (TRONCO, 'troncos', 'cenario'),
                       (COPA, 'copas', 'folhas'), (COPA_RUA, 'copas_rua', 'folhas'), (ARV_N, 'arvore_ninho', 'cenario'), (COPA_N, 'copa_ninho', 'folhas'),
                       (COLI, 'colisao', 'colisao')):
    ob = geo.obj(nome, mat)
    saidas.append(ob)
    print('OBJ', nome, 'vertices', len(geo.v), 'triangulos', sum(len(f) - 2 for f in geo.f))
ctx = CTX.obj('contexto', 'contexto')
bpy.data.objects['colisao'].hide_render = True


def exportar(path, objs):
    for o in bpy.data.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    rna = bpy.ops.export_scene.gltf.get_rna_type().properties
    props = rna.keys()
    kw = dict(filepath=path, export_format='GLB')
    for k, v in (('use_selection', True), ('export_yup', True), ('export_apply', True), ('export_animations', False),
                 ('export_cameras', False), ('export_lights', False), ('export_texcoords', False), ('export_normals', False)):
        if k in props:
            kw[k] = v
    if 'export_vertex_color' in props:
        items = rna['export_vertex_color'].enum_items.keys()
        kw['export_vertex_color'] = 'ACTIVE' if 'ACTIVE' in items else items[0]
    elif 'export_colors' in props:
        kw['export_colors'] = True
    bpy.ops.export_scene.gltf(**kw)
    print('EXPORTADO', os.path.basename(path), 'bytes', os.path.getsize(path))


exportar(os.path.join(OUT, 'praca.glb'), saidas)

# ---------- prévias ----------
B = lambda p: Vector((p[0], -p[2], p[1]))


def previas_praca(views, res=(900, 600), cols=2):
    sc = bpy.context.scene
    engines = bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys()
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    world = bpy.data.worlds.new('ceu')
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*lin(0xbfe0f5), 1)
    bg.inputs[1].default_value = 0.9
    sol = bpy.data.lights.new('sol', 'SUN')
    sol.energy = 3.2
    sol.angle = math.radians(3)
    so = bpy.data.objects.new('sol', sol)
    so.rotation_euler = (Vector((0, 0, 0)) - B((16, 32, 14))).to_track_quat('-Z', 'Y').to_euler()
    colecao().objects.link(so)
    cd = bpy.data.cameras.new('cam')
    cd.lens = 24
    cd.clip_end = 400
    cam = bpy.data.objects.new('cam', cd)
    colecao().objects.link(cam)
    sc.camera = cam
    paths = []
    for nome, pos, alvo in views:
        look(cam, B(pos), B(alvo))
        sc.render.filepath = os.path.join(OUT, 'previa_praca_%s.png' % nome)
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
    W, H = res
    rows = (len(paths) + cols - 1) // cols
    grid = np.ones((H * rows, W * cols, 4), dtype=np.float32)
    for i, p in enumerate(paths):
        im = bpy.data.images.load(p)
        a = np.array(im.pixels[:], dtype=np.float32).reshape(H, W, 4)
        r, c = divmod(i, cols)
        grid[(rows - 1 - r) * H:(rows - r) * H, c * W:(c + 1) * W] = a
    img = bpy.data.images.new('folha', W * cols, H * rows, alpha=True)
    img.pixels = grid.ravel()
    img.filepath_raw = os.path.join(OUT, 'previa_praca.png')
    img.file_format = 'PNG'
    img.save()
    print('FOLHA', img.filepath_raw)


if '--sem-previa' not in sys.argv:
    previas_praca([
        ('aerea', (26, 22, 30), (0, 0, 0)),
        ('norte', (4, 3.2, 6), (-2, 6, -30)),
        ('ninho', (4.2, 4.6, -2.4), (8.2, 4.8, -6.6)),
        ('coreto', (-3.2, 2.2, -2.0), (-10, 2.0, -10)),
        ('banca', (-8, 2.4, 9.5), (-16, 2.4, 17)),
        ('chafariz', (6.5, 2.3, 7.5), (0, 1.4, 0)),
    ])
