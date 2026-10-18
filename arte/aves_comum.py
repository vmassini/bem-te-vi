"""Ferramentas compartilhadas para modelar as aves do jogo no Blender.

Cada script de espécie faz:  iniciar() -> constrói peças -> exportar_glb() -> previas().
Eixos no Blender: frente = -Y, cima = +Z, lado = X. O glTF exportado fica com frente +Z e cima +Y (como no jogo).
Cores ficam no atributo de vértice "Col" (espaço linear).
"""
import bpy, bmesh, math, os, sys, json
from mathutils import Vector, Matrix, Euler
import numpy as np

ZERO = Vector((0, 0, 0))


# ---------- argumentos e pastas ----------
def argumentos():
    return sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def pasta_saida(padrao):
    a = argumentos()
    out = os.path.abspath(a[0]) if a else padrao
    os.makedirs(out, exist_ok=True)
    return out


# ---------- cores ----------
def lin(h):
    c = [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def paleta(d):
    return {k: lin(v) for k, v in d.items()}


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def sst(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ---------- cena e materiais ----------
M = {}


def colecao():
    return bpy.context.scene.collection


def material(name, rough=0.75, double=False, spec=0.25):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get('Principled BSDF')
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Col'
    nt.links.new(vc.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    for key in ('Specular IOR Level', 'Specular'):
        if key in b.inputs:
            b.inputs[key].default_value = spec
            break
    m.use_backface_culling = not double
    return m


def iniciar():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M.clear()
    M['plumagem'] = material('plumagem', 0.8)
    M['penas'] = material('penas', 0.75, double=True)
    M['bico'] = material('bico', 0.35, spec=0.5)
    M['olho'] = material('olho', 0.08, spec=0.9)


def set_colors(me, cols):
    a = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
    flat = []
    for c in cols:
        flat.extend((c[0], c[1], c[2], 1.0))
    a.data.foreach_set('color', flat)
    for attr in ('active_color', 'render_color'):
        try:
            setattr(me.color_attributes, attr, a)
        except Exception:
            pass
    try:
        me.color_attributes.active_color_name = 'Col'
    except Exception:
        pass


def recalc_normals(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()


class Malha:
    """Acumula vértices, faces e cores e vira um objeto no fim."""
    def __init__(self):
        self.v, self.f, self.c = [], [], []

    def add(self, verts, faces, cols):
        o = len(self.v)
        self.v.extend(Vector(v) for v in verts)
        self.c.extend(cols)
        self.f.extend(tuple(i + o for i in fc) for fc in faces)

    def obj(self, name, mat, origin=ZERO, smooth=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v - origin) for v in self.v], [], self.f)
        me.update()
        recalc_normals(me)
        set_colors(me, self.c)
        for p in me.polygons:
            p.use_smooth = smooth
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        colecao().objects.link(ob)
        return ob


# ---------- formas orgânicas: união de elipsoides, remalhada e suavizada ----------
def blob(name, parts, voxel=0.004, smooth=(0.75, 12), faces=3500, mat=None):
    bm = bmesh.new()
    for c, r, rot in parts:
        m = Matrix.LocRotScale(Vector(c), Euler(rot).to_quaternion(), Vector(r))
        bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=24, radius=1.0, matrix=m)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    colecao().objects.link(ob)
    md = ob.modifiers.new('remalha', 'REMESH')
    md.mode = 'VOXEL'
    md.voxel_size = voxel
    sm = ob.modifiers.new('suaviza', 'SMOOTH')
    sm.factor = smooth[0]
    sm.iterations = smooth[1]
    bpy.context.view_layer.update()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    ob.modifiers.clear()
    ob.data = me2
    if len(me2.polygons) > faces:
        d = ob.modifiers.new('reduz', 'DECIMATE')
        d.ratio = faces / len(me2.polygons)
        bpy.context.view_layer.update()
        me3 = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        ob.modifiers.clear()
        ob.data = me3
    ob.data.name = name
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.materials.append(mat or M['plumagem'])
    return ob


def paint(ob, fn):
    me = ob.data
    set_colors(me, [fn(v.co.copy(), v.normal.copy()) for v in me.vertices])


def inflar(ob, nome, dist, fn, mat=None):
    """Cópia da malha empurrada para fora (camada de plumagem por cima)."""
    me = ob.data.copy()
    me.name = nome
    for v in me.vertices:
        v.co = v.co + v.normal * dist
    me.color_attributes.remove(me.color_attributes['Col'])
    o2 = bpy.data.objects.new(nome, me)
    colecao().objects.link(o2)
    paint(o2, fn)
    if mat:
        me.materials.clear()
        me.materials.append(mat)
    return o2


def hit(ob, origin, direction):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ok, loc, nor, _ = ob.ray_cast(Vector(origin), Vector(direction).normalized(), depsgraph=dg)
    return (loc, nor) if ok else (None, None)


# ---------- peças: pena, tubo, esfera, bico ----------
def frame(origin, xdir, up):
    X = Vector(xdir).normalized()
    Y = Vector(up).cross(X).normalized()
    Z = X.cross(Y)
    return Vector(origin), X, Y, Z


def pena(mal, fr, L, W, base, borda, ponta, curva=0.1, arco=0.25, assim=0.7, lado=1, faixas=0, cor_faixa=None, nl=7, nw=2, fio=0.45):
    """Pena achatada: comprimento em X do quadro, largura em Y, curvatura em Z. fio = início da borda colorida."""
    o, X, Y, Z = fr
    verts, cols, faces = [], [], []
    for i in range(nl + 1):
        u = i / nl
        w = W * (0.3 + 0.7 * u / 0.55) if u <= 0.55 else W * math.sqrt(max(0.0, 1 - ((u - 0.55) / 0.45) ** 2))
        for j in range(-nw, nw + 1):
            v = j / nw
            ly = v * w * (1.0 if v * lado >= 0 else assim)
            lz = -curva * L * u * u + arco * w * (1 - v * v) * 0.5
            verts.append(o + X * (u * L) + Y * ly + Z * lz)
            c = borda if v * lado > fio else base
            if faixas and math.sin(u * math.pi * faixas * 2) > 0.5:
                c = cor_faixa
            if j == 0:
                c = mix(c, borda, 0.25)
            if u > 0.8:
                c = mix(c, ponta, sst(0.8, 1.0, u))
            cols.append(c)
    row = 2 * nw + 1
    for i in range(nl):
        for j in range(row - 1):
            a = i * row + j
            faces.append((a, a + 1, a + row + 1, a + row))
    mal.add(verts, faces, cols)


def tubo(mal, pts, raios, cores, seg=8):
    pts = [Vector(p) for p in pts]
    n = len(pts)
    verts, faces, cols = [], [], []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
        a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(a).normalized()
        v = t.cross(u)
        for k in range(seg):
            ang = 2 * math.pi * k / seg
            verts.append(p + (u * math.cos(ang) + v * math.sin(ang)) * raios[i])
            cols.append(cores[i])
    for i in range(n - 1):
        for k in range(seg):
            a = i * seg + k
            b = i * seg + (k + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    c0 = len(verts); verts.append(pts[0]); cols.append(cores[0])
    c1 = len(verts); verts.append(pts[-1]); cols.append(cores[-1])
    last = (n - 1) * seg
    for k in range(seg):
        faces.append((c0, (k + 1) % seg, k))
        faces.append((c1, last + k, last + (k + 1) % seg))
    mal.add(verts, faces, cols)


def esfera(mal, c, r, cor_fn, seg=16, rings=10):
    verts, faces, cols = [], [], []
    for i in range(rings + 1):
        th = math.pi * i / rings
        for k in range(seg):
            ph = 2 * math.pi * k / seg
            n = Vector((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
            verts.append(Vector(c) + Vector((n.x * r[0], n.y * r[1], n.z * r[2])))
            cols.append(cor_fn(n))
    for i in range(rings):
        for k in range(seg):
            a = i * seg + k
            b = i * seg + (k + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    mal.add(verts, faces, cols)


def bico(mal, base, L, W, Hu, Hl, gancho, superior, cor, n_len=10, n_ring=14, cor_fn=None):
    """Metade de cima ou de baixo de um bico afilado. cor_fn(t, s) recebe t (0 base -> 1 ponta) e s (-1 baixo .. 1 cima)."""
    rings, cols = [], []
    for i in range(n_len + 1):
        t = i / n_len
        w = W * 0.5 * (1 - t) ** 0.75 + 0.0008
        hu = Hu * (1 - t) ** 0.85 + 0.0005
        hl = Hl * (1 - t) ** 0.9 + 0.0004
        y = base.y - L * t
        zc = base.z - gancho * t ** 3
        ring = []
        for j in range(n_ring):
            a = 2 * math.pi * j / n_ring
            sx, sz = math.cos(a), math.sin(a)
            if superior:
                z = zc + (hu * sz if sz > 0 else 0.12 * hu * sz)
            else:
                z = zc - 0.003 + (hl * sz if sz < 0 else 0.1 * hl * sz)
            ring.append(Vector((base.x + w * sx, y, z)))
            cols.append(cor_fn(t, sz) if cor_fn else cor)
        rings.append(ring)
    verts = [p for r in rings for p in r]
    faces = []
    for i in range(n_len):
        for j in range(n_ring):
            a = i * n_ring + j
            b = i * n_ring + (j + 1) % n_ring
            faces.append((a, b, b + n_ring, a + n_ring))
    mal.add(verts, faces, cols)


def olho(m, centro, out, raio, cor_iris, cor_pupila, cor_brilho, pupila=0.8):
    esfera(m, centro, (raio, raio, raio), lambda n: cor_pupila if n.dot(out) > pupila else cor_iris, 14, 10)
    esfera(m, centro + out * raio * 0.88 + Vector((0, -0.18 * raio, 0.24 * raio)), (raio * 0.25,) * 3, lambda n: cor_brilho, 8, 6)


# ---------- hierarquia ----------
def empty(name, glob, parent=None, parent_glob=ZERO):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.03
    colecao().objects.link(e)
    e.location = Vector(glob) - parent_glob
    e.parent = parent
    return e


def attach(ob, parent, pivot):
    ob.data.transform(Matrix.Translation(-Vector(pivot)))
    ob.parent = parent
    ob.location = (0, 0, 0)
    return ob


# ---------- exportação ----------
def triangulos():
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')


def exportar_glb(path):
    bpy.context.view_layer.update()
    rna = bpy.ops.export_scene.gltf.get_rna_type().properties
    props = rna.keys()
    kw = dict(filepath=path, export_format='GLB')
    for k, v in (('export_yup', True), ('export_apply', True), ('export_animations', False),
                 ('export_cameras', False), ('export_lights', False), ('export_texcoords', False)):
        if k in props:
            kw[k] = v
    if 'export_vertex_color' in props:
        items = rna['export_vertex_color'].enum_items.keys()
        kw['export_vertex_color'] = 'ACTIVE' if 'ACTIVE' in items else items[0]
    elif 'export_colors' in props:
        kw['export_colors'] = True
    tris = triangulos()
    bpy.ops.export_scene.gltf(**kw)
    print('EXPORTADO', os.path.basename(path), 'triângulos:', tris)
    return tris


# ---------- prévias renderizadas ----------
def look(obj, pos, target):
    obj.location = Vector(pos)
    obj.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()


def previas(out, nome, views, pose, res=600, cols=4, galho_z=-0.189):
    """views: [(nome, kwargs_da_pose, posição_da_câmera, alvo)]. A pose recebe os kwargs e deve
    mostrar/esconder o objeto 'galho' se a espécie usar poleiro."""
    sc = bpy.context.scene
    engines = bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items.keys()
    sc.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engines else 'BLENDER_EEVEE'
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    try:
        sc.view_settings.view_transform = 'Standard'
    except Exception:
        pass
    for attr in ('use_gtao', 'use_soft_shadows'):
        if hasattr(sc.eevee, attr):
            setattr(sc.eevee, attr, True)
    world = bpy.data.worlds.new('mundo')
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*lin(0xcfe3f2), 1)
    bg.inputs[1].default_value = 1.0
    sun = bpy.data.lights.new('sol', 'SUN')
    sun.energy = 3.0
    sun.angle = math.radians(10)
    so = bpy.data.objects.new('sol', sun)
    so.rotation_euler = (math.radians(48), 0, math.radians(-38))
    colecao().objects.link(so)
    fill = bpy.data.lights.new('rebatedor', 'AREA')
    fill.energy = 18
    fill.size = 1.5
    fo = bpy.data.objects.new('rebatedor', fill)
    colecao().objects.link(fo)
    gm = bpy.data.materials.new('galho')
    gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*lin(0x6b4423), 1)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=0.035, radius2=0.03, depth=1.4,
                          matrix=Matrix.Translation((0, 0, galho_z - 0.034)) @ Matrix.Rotation(math.pi / 2, 4, 'Y'))
    gme = bpy.data.meshes.new('galho')
    bm.to_mesh(gme)
    bm.free()
    for p in gme.polygons:
        p.use_smooth = True
    gme.materials.append(gm)
    galho = bpy.data.objects.new('galho', gme)
    colecao().objects.link(galho)
    galho.hide_render = True
    cam_data = bpy.data.cameras.new('cam')
    cam_data.lens = 70
    cam = bpy.data.objects.new('cam', cam_data)
    colecao().objects.link(cam)
    sc.camera = cam
    paths = []
    for vnome, kw, cpos, ctarget in views:
        pose(**kw)
        look(cam, cpos, ctarget)
        look(fo, Vector(cpos) * 1.6 + Vector((0.6, 0, 0.6)), ctarget)
        sc.render.filepath = os.path.join(out, 'previa_%s_%s.png' % (nome, vnome))
        bpy.ops.render.render(write_still=True)
        paths.append(sc.render.filepath)
    rows = (len(paths) + cols - 1) // cols
    grid = np.zeros((res * rows, res * cols, 4), dtype=np.float32)
    grid[..., :3] = np.array(lin(0xcfe3f2))
    grid[..., 3] = 1
    for i, p in enumerate(paths):
        im = bpy.data.images.load(p)
        a = np.array(im.pixels[:], dtype=np.float32).reshape(res, res, 4)
        r, c = divmod(i, cols)
        grid[(rows - 1 - r) * res:(rows - r) * res, c * res:(c + 1) * res] = a   # pixels do Blender vêm de baixo para cima
    img = bpy.data.images.new('folha', res * cols, res * rows, alpha=True)
    img.pixels = grid.ravel()
    img.filepath_raw = os.path.join(out, 'previa_%s.png' % nome)
    img.file_format = 'PNG'
    img.save()
    print('FOLHA', img.filepath_raw)
