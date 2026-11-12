"""Example: a procedural mothership in Blender (Cycles, headless Python). HOME-specific, kept as a worked example.

This is the CG insert built for HOME (a 2-minute sci-fi short made with the still-to-film pipeline): the generated
stills of the ship could not fly into frame, so the ship was rebuilt procedurally and rendered as video shots and as
transparent sprites for depth shots. Read it for patterns, not as a library. Tested on Blender 5.3; most of it runs on 4.x.

  blender -b --factory-startup -P mothership.py -- --shot s01 --stills 1,48,96 --pct 50 --samples 32
  blender -b --factory-startup -P mothership.py -- --shot s05 --anim --pct 100 --samples 48
  blender -b --factory-startup -P mothership.py -- --shot sprite        # transparent side view for depthshot sprites

Outputs go to ./tests (stills) and ./renders/ms_<shot>/ (frames) next to this file. Encode frames with ffmpeg.
Patterns worth stealing (see ../../references/pitfalls.md for the API gotchas):
  - geometry from bmesh: hull by lathe(), lattice booms from bevelled curves (curve_obj())
  - animated emission "plumes" (PlumeW / PlumeGain) for engine fire
  - look_axis(): solve camera roll so the ship's axis reads the way you want on screen
  - compositor glare through scene.compositing_node_group (Blender 5.x)

Original notes:
HOME mothership, procedural (Blender 5.3, Cycles).  1 unit = 100 m, ship ~1 km, nose toward +Y.

  blender -b -P mothership.py -- --shot s01 --stills 1,48,96 --pct 50 --samples 32
  blender -b -P mothership.py -- --shot s01 --anim --pct 75 --samples 32

Design from the person's stills: slender dark hull with hex heat tiles and blue-white light strips, twin aft
engine nacelles with blue plasma plumes, two orange lattice booms with gold-foil collars, one 6-spoke
habitat ring (rotating), a bridge saucer on the nose, a lit hangar bay on the flank, small shuttles.
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default=None, cast=str):
    if name in argv:
        i = argv.index(name)
        return cast(argv[i + 1]) if i + 1 < len(argv) and not argv[i + 1].startswith('--') else True
    return default

FPS = 30

# ----------------------------------------------------------------------------- helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    except Exception:
        pass

def new_mat(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    return m, nt, nt.nodes.new('ShaderNodeOutputMaterial')

def N(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        if k.startswith('_'):
            setattr(n, k[1:], v)
        else:
            n.inputs[k].default_value = v
    return n

def L(nt, a, b):
    nt.links.new(a, b)

def M(nt, op, a, b=None, clamp=False):
    m = nt.nodes.new('ShaderNodeMath'); m.operation = op; m.use_clamp = clamp
    for i, v in ((0, a), (1, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            m.inputs[i].default_value = v
        else:
            nt.links.new(v, m.inputs[i])
    return m.outputs[0]

def V(nt, op, a, b=None):
    m = nt.nodes.new('ShaderNodeVectorMath'); m.operation = op
    for i, v in ((0, a), (1, b)):
        if v is None:
            continue
        if isinstance(v, (tuple, list)):
            m.inputs[i].default_value = v
        else:
            nt.links.new(v, m.inputs[i])
    return m.outputs['Vector'] if op not in ('LENGTH', 'DOT_PRODUCT', 'DISTANCE') else m.outputs['Value']

def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj

def mesh_from_bm(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    if mat:
        me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))

def lathe(name, profile, seg, mat, axis_y=True, cap=True):
    """profile: list of (y, r). Revolved around Y. UV: u around, v along the profile."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.verify()
    rows = []
    for (y, r) in profile:
        rows.append([bm.verts.new((r * math.cos(2 * math.pi * j / seg), y, r * math.sin(2 * math.pi * j / seg))) for j in range(seg)])
    tot = len(profile) - 1
    for i in range(tot):
        for j in range(seg):
            j2 = (j + 1) % seg
            f = bm.faces.new((rows[i][j], rows[i][j2], rows[i + 1][j2], rows[i + 1][j]))
            for lp, (uu, vv) in zip(f.loops, ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1))):
                lp[uvl].uv = (uu / seg, vv / tot)
    if cap:
        for row in (rows[0], rows[-1]):
            if row[0].co.length > 1e-6:
                try:
                    bm.faces.new(row if row is rows[-1] else list(reversed(row)))
                except Exception:
                    pass
    return mesh_from_bm(name, bm, mat)

def curve_obj(name, polylines, bevel, mat, res=2):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = bevel; cu.bevel_resolution = res
    for pts in polylines:
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for k, p in enumerate(pts):
            sp.points[k].co = (p[0], p[1], p[2], 1)
    o = link(bpy.data.objects.new(name + '_c', cu))
    me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(o); bpy.data.curves.remove(cu)
    me.materials.clear(); me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))

def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = name
    return o

# ----------------------------------------------------------------------------- materials
def mat_hull():
    """dark blue-grey ceramic composite: hex heat tiles, panel seams, dashed light strips, amber windows"""
    m, nt, out = new_mat('MS_Hull')
    uv = N(nt, 'ShaderNodeUVMap')
    sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, uv.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    # hex grid in (u*U, v*Vv)
    p = N(nt, 'ShaderNodeCombineXYZ')
    L(nt, M(nt, 'MULTIPLY', u, 95.0), p.inputs['X']); L(nt, M(nt, 'MULTIPLY', v, 330.0), p.inputs['Y'])
    pv = p.outputs[0]
    R = (1.0, 1.7320508, 1.0); H = (0.5, 0.8660254, 0.5)
    def hexcell(q):
        f = V(nt, 'FRACTION', V(nt, 'DIVIDE', q, R))
        return V(nt, 'SUBTRACT', V(nt, 'MULTIPLY', f, R), H)
    a = hexcell(pv); b = hexcell(V(nt, 'SUBTRACT', pv, H))
    la, lb = V(nt, 'LENGTH', a), V(nt, 'LENGTH', b)
    pick = M(nt, 'LESS_THAN', la, lb)
    mixv = N(nt, 'ShaderNodeMix', _data_type='VECTOR'); L(nt, pick, mixv.inputs['Factor'])
    L(nt, b, mixv.inputs[4]); L(nt, a, mixv.inputs[5])
    g = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, mixv.outputs[1], g.inputs[0])
    ax, ay = M(nt, 'ABSOLUTE', g.outputs['X']), M(nt, 'ABSOLUTE', g.outputs['Y'])
    hd = M(nt, 'MAXIMUM', M(nt, 'ADD', M(nt, 'MULTIPLY', ax, 0.5), M(nt, 'MULTIPLY', ay, 0.8660254)), ax)
    seam = M(nt, 'SMOOTH_MIN', 1.0, M(nt, 'MULTIPLY', M(nt, 'SUBTRACT', 0.5, hd), 28.0))   # 0 at seams -> 1 inside
    seam = M(nt, 'MINIMUM', M(nt, 'MAXIMUM', seam, 0.0), 1.0)
    # per-tile tint
    cell_id = V(nt, 'SUBTRACT', pv, mixv.outputs[1])
    wn = N(nt, 'ShaderNodeTexWhiteNoise', _noise_dimensions='3D'); L(nt, V(nt, 'FLOOR', V(nt, 'MULTIPLY', cell_id, (2.0, 2.0, 1.0))), wn.inputs['Vector'])
    tint = M(nt, 'ADD', 0.85, M(nt, 'MULTIPLY', wn.outputs['Value'], 0.3))
    # large panel seams every few metres (rectangular)
    pu = M(nt, 'FRACT', M(nt, 'MULTIPLY', u, 24.0)); pvv = M(nt, 'FRACT', M(nt, 'MULTIPLY', v, 60.0))
    panel = M(nt, 'MULTIPLY', M(nt, 'SMOOTHERSTEP' if False else 'MINIMUM', M(nt, 'MULTIPLY', pu, 60.0), 1.0),
              M(nt, 'MINIMUM', M(nt, 'MULTIPLY', pvv, 90.0), 1.0))
    base = N(nt, 'ShaderNodeCombineColor')
    c = M(nt, 'MULTIPLY', tint, M(nt, 'ADD', 0.35, M(nt, 'MULTIPLY', M(nt, 'MULTIPLY', seam, panel), 0.65)))
    L(nt, M(nt, 'MULTIPLY', c, 0.16), base.inputs['Red']); L(nt, M(nt, 'MULTIPLY', c, 0.175), base.inputs['Green'])
    L(nt, M(nt, 'MULTIPLY', c, 0.20), base.inputs['Blue'])
    # light strips: four dashed lines at fixed angles, amber window rows
    def band(center, width):
        d = M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', M(nt, 'FRACT', M(nt, 'ADD', u, 1.0 - center)), 0.5))
        return M(nt, 'LESS_THAN', M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', d, 0.5)), width)
    dash = M(nt, 'GREATER_THAN', M(nt, 'FRACT', M(nt, 'MULTIPLY', v, 140.0)), 0.35)
    strips = M(nt, 'MULTIPLY', M(nt, 'ADD', M(nt, 'ADD', band(0.25, 0.0025), band(0.75, 0.0025)), band(0.0, 0.002)), dash)
    win_rows = M(nt, 'ADD', band(0.18, 0.004), band(0.32, 0.004))
    wcell = N(nt, 'ShaderNodeCombineXYZ'); L(nt, M(nt, 'FLOOR', M(nt, 'MULTIPLY', v, 400.0)), wcell.inputs['X']); L(nt, M(nt, 'FLOOR', M(nt, 'MULTIPLY', u, 300.0)), wcell.inputs['Y'])
    wn2 = N(nt, 'ShaderNodeTexWhiteNoise', _noise_dimensions='3D'); L(nt, wcell.outputs[0], wn2.inputs['Vector'])
    wins = M(nt, 'MULTIPLY', win_rows, M(nt, 'GREATER_THAN', wn2.outputs['Value'], 0.55))
    em = N(nt, 'ShaderNodeMix', _data_type='RGBA', Factor=0.0)
    L(nt, M(nt, 'DIVIDE', wins, M(nt, 'ADD', M(nt, 'ADD', wins, strips), 0.0001)), em.inputs['Factor'])
    em.inputs[6].default_value = (0.55, 0.78, 1.0, 1); em.inputs[7].default_value = (1.0, 0.62, 0.28, 1)
    bump = N(nt, 'ShaderNodeBump', Strength=0.6, Distance=0.006)
    L(nt, M(nt, 'MULTIPLY', seam, panel), bump.inputs['Height'])
    bsdf = N(nt, 'ShaderNodeBsdfPrincipled', Metallic=0.55, Roughness=0.42)
    L(nt, base.outputs[0], bsdf.inputs['Base Color']); L(nt, bump.outputs['Normal'], bsdf.inputs['Normal'])
    rn = N(nt, 'ShaderNodeTexNoise', Scale=40.0, Detail=6.0); L(nt, uv.outputs['UV'], rn.inputs['Vector'])
    L(nt, M(nt, 'ADD', 0.3, M(nt, 'MULTIPLY', rn.outputs['Fac'], 0.3)), bsdf.inputs['Roughness'])
    L(nt, em.outputs[2], bsdf.inputs['Emission Color'])
    L(nt, M(nt, 'MULTIPLY', M(nt, 'ADD', M(nt, 'MULTIPLY', strips, 1.4), M(nt, 'MULTIPLY', wins, 4.0)), 1.0), bsdf.inputs['Emission Strength'])
    L(nt, bsdf.outputs[0], out.inputs['Surface'])
    return m

def mat_metal(name, col, rough=0.35, metallic=1.0):
    m, nt, out = new_mat(name)
    b = N(nt, 'ShaderNodeBsdfPrincipled', Metallic=metallic, Roughness=rough, **{'Base Color': (*col, 1)})
    L(nt, b.outputs[0], out.inputs['Surface'])
    return m

def mat_foil():
    m, nt, out = new_mat('MS_Foil')
    tc = N(nt, 'ShaderNodeTexCoord')
    nz = N(nt, 'ShaderNodeTexNoise', Scale=60.0, Detail=8.0, Roughness=0.7)
    L(nt, tc.outputs['Object'], nz.inputs['Vector'])
    bump = N(nt, 'ShaderNodeBump', Strength=0.9, Distance=0.01); L(nt, nz.outputs['Fac'], bump.inputs['Height'])
    b = N(nt, 'ShaderNodeBsdfPrincipled', Metallic=1.0, Roughness=0.22, **{'Base Color': (1.0, 0.72, 0.30, 1)})
    L(nt, bump.outputs['Normal'], b.inputs['Normal']); L(nt, b.outputs[0], out.inputs['Surface'])
    return m

def mat_emit(name, col, strength, camera_only=False):
    m, nt, out = new_mat(name)
    em = N(nt, 'ShaderNodeEmission', Color=(*col, 1), Strength=strength); em.name = 'Emit'
    L(nt, em.outputs[0], out.inputs['Surface'])
    return m

def mat_ringwin():
    """habitat ring: bronze structure with a band of lit windows"""
    m, nt, out = new_mat('MS_Ring')
    uv = N(nt, 'ShaderNodeUVMap'); sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, uv.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    band = M(nt, 'LESS_THAN', M(nt, 'ABSOLUTE', M(nt, 'SUBTRACT', v, 0.5)), 0.12)
    cells = M(nt, 'GREATER_THAN', M(nt, 'FRACT', M(nt, 'MULTIPLY', u, 220.0)), 0.3)
    cw = N(nt, 'ShaderNodeCombineXYZ'); L(nt, M(nt, 'FLOOR', M(nt, 'MULTIPLY', u, 220.0)), cw.inputs['X'])
    wn = N(nt, 'ShaderNodeTexWhiteNoise', _noise_dimensions='3D'); L(nt, cw.outputs[0], wn.inputs['Vector'])
    lit = M(nt, 'MULTIPLY', M(nt, 'MULTIPLY', band, cells), M(nt, 'GREATER_THAN', wn.outputs['Value'], 0.25))
    b = N(nt, 'ShaderNodeBsdfPrincipled', Metallic=0.9, Roughness=0.33, **{'Base Color': (0.42, 0.33, 0.22, 1)})
    b.inputs['Emission Color'].default_value = (1.0, 0.66, 0.32, 1)
    L(nt, M(nt, 'MULTIPLY', lit, 3.5), b.inputs['Emission Strength'])
    L(nt, b.outputs[0], out.inputs['Surface'])
    return m

def mat_plume():
    """engine plume: blue-white core, soft blue sheath, shock diamonds, animated flicker (4D noise W = frame)"""
    m, nt, out = new_mat('MS_Plume')
    tc = N(nt, 'ShaderNodeTexCoord'); sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, tc.outputs['Generated'], sep.inputs[0])
    t = M(nt, 'SUBTRACT', 1.0, sep.outputs['Y'])               # Generated Y is 0 at the tail -> flip: 0 at the nozzle
    lw = N(nt, 'ShaderNodeLayerWeight', Blend=0.5)
    core = M(nt, 'POWER', M(nt, 'SUBTRACT', 1.0, lw.outputs['Facing']), 2.2)   # bright where we look through the middle
    fall = M(nt, 'POWER', M(nt, 'SUBTRACT', 1.0, t), 1.6)
    diamonds = M(nt, 'ADD', 0.75, M(nt, 'MULTIPLY', 0.25, M(nt, 'COSINE', M(nt, 'MULTIPLY', t, 2 * math.pi * 5.0))))
    nz = N(nt, 'ShaderNodeTexNoise', _noise_dimensions='4D', Scale=6.0, Detail=3.0)
    L(nt, tc.outputs['Object'], nz.inputs['Vector'])
    wv = N(nt, 'ShaderNodeValue', _name='PlumeW'); wv.outputs[0].default_value = 0.0
    L(nt, wv.outputs[0], nz.inputs['W'])
    flick = M(nt, 'ADD', 0.7, M(nt, 'MULTIPLY', nz.outputs['Fac'], 0.6))
    a = M(nt, 'MULTIPLY', M(nt, 'MULTIPLY', core, fall), M(nt, 'MULTIPLY', diamonds, flick), clamp=True)
    col = N(nt, 'ShaderNodeMix', _data_type='RGBA'); L(nt, M(nt, 'POWER', core, 3.0), col.inputs['Factor'])
    col.inputs[6].default_value = (0.10, 0.35, 1.0, 1); col.inputs[7].default_value = (0.6, 0.85, 1.0, 1)
    em = N(nt, 'ShaderNodeEmission'); L(nt, col.outputs[2], em.inputs['Color'])
    gain = N(nt, 'ShaderNodeValue', _name='PlumeGain'); gain.outputs[0].default_value = 1.0
    L(nt, M(nt, 'MULTIPLY', M(nt, 'MULTIPLY', a, 5.0), gain.outputs[0]), em.inputs['Strength'])
    tr = N(nt, 'ShaderNodeBsdfTransparent'); add = N(nt, 'ShaderNodeAddShader')
    L(nt, tr.outputs[0], add.inputs[0]); L(nt, em.outputs[0], add.inputs[1])
    L(nt, add.outputs[0], out.inputs['Surface'])
    return m

# ----------------------------------------------------------------------------- the ship
def build_ship(mats):
    parts, coll = [], bpy.data.collections.new('Mothership')
    bpy.context.scene.collection.children.link(coll)
    # main hull: lathe profile (y, r), nose at +Y
    prof = [(5.05, 0.0), (5.0, 0.07), (4.85, 0.15), (4.5, 0.22), (3.8, 0.27), (2.0, 0.32), (0.0, 0.35), (-1.5, 0.36),
            (-2.4, 0.37), (-2.9, 0.40), (-3.1, 0.38)]
    hull = lathe('ms_hull', prof, 128, mats['hull'])
    hull.scale.x = 1.12                                      # slightly wide oval section
    parts.append(hull)
    # dorsal spine with a light strip
    sp = lathe('ms_spine', [(4.2, 0.0), (4.1, 0.03), (-2.6, 0.035), (-2.7, 0.0)], 12, mats['hull'])
    sp.location.z = 0.31; parts.append(sp)
    # twin engine nacelles
    for sx in (-1, 1):
        nac = lathe(f'ms_nac{sx}', [(-1.9, 0.0), (-2.0, 0.20), (-2.4, 0.30), (-3.2, 0.33), (-4.6, 0.33), (-4.75, 0.31), (-4.8, 0.26)],
                    96, mats['hull'], cap=False)
        nac.location.x = sx * 0.33; parts.append(nac)
        for k, (y, r) in enumerate([(-4.80, 0.30), (-4.78, 0.27), (-4.75, 0.235), (-4.72, 0.20), (-4.69, 0.17)]):       # concentric nozzle rings
            bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.018, major_segments=72, minor_segments=8,
                                             location=(sx * 0.33, y, 0), rotation=(math.pi / 2, 0, 0))
            o = bpy.context.active_object; o.data.materials.append(mats['rib']); parts.append(o)
        bm = bmesh.new()                                    # glowing core disc
        bmesh.ops.create_circle(bm, cap_ends=True, segments=48, radius=0.16)
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
        bmesh.ops.translate(bm, verts=bm.verts, vec=(sx * 0.33, -4.69, 0))
        parts.append(mesh_from_bm(f'ms_core{sx}', bm, mats['core'], smooth=False))
        cone = lathe(f'ms_cone{sx}', [(-4.69, 0.16), (-4.55, 0.07), (-4.5, 0.0)], 32, mats['core'], cap=False)
        cone.location.x = sx * 0.33; parts.append(cone)
    # bridge saucer + dome + antennas on the nose
    sau = lathe('ms_saucer', [(0.06, 0.0), (0.06, 0.20), (0.03, 0.30), (-0.03, 0.31), (-0.06, 0.24), (-0.06, 0.0)], 64, mats['rib'])
    sau.rotation_euler = (math.pi / 2, 0, 0); sau.location = (0, 3.65, 0.30); parts.append(sau)
    win = lathe('ms_bridgewin', [(0.012, 0.302), (-0.012, 0.308)], 64, mats['bridge'], cap=False)
    win.rotation_euler = (math.pi / 2, 0, 0); win.location = (0, 3.65, 0.30); parts.append(win)
    for (x, y, h) in ((0.05, 3.62, 0.32), (-0.07, 3.70, 0.22), (0.0, 3.55, 0.26)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.006, depth=h, location=(x, y, 0.36 + h / 2))
        o = bpy.context.active_object; o.data.materials.append(mats['rib']); parts.append(o)
    # hangar bay: lit recess on the +X flank
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, verts=bm.verts, vec=(1.0, 1.6, 1.0))
    bmesh.ops.scale(bm, verts=bm.verts, vec=(0.22, 1.0, 1.0))
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0.345, 1.1, -0.03))
    parts.append(mesh_from_bm('ms_hangar', bm, mats['hangar'], smooth=False))
    # greebles along the hull
    rnd = random.Random(3); bm = bmesh.new()
    for k in range(4200):
        y = rnd.uniform(-2.6, 4.3); a = rnd.uniform(0, 2 * math.pi)
        r = 0.32 * 1.0 + 0.0
        nrm = Vector((math.cos(a) * 1.12, 0, math.sin(a))).normalized()
        big = rnd.random() < 0.12
        w, l, h = (rnd.uniform(0.04, 0.10), rnd.uniform(0.10, 0.35), rnd.uniform(0.006, 0.02)) if big else (rnd.uniform(0.008, 0.035), rnd.uniform(0.015, 0.10), rnd.uniform(0.003, 0.018))
        tan = Vector((-nrm.z, 0, nrm.x))
        Mx = Matrix((tan, (0, 1, 0), nrm)).transposed().to_4x4()
        rr = 0.29 + 0.03 * (y + 2.6) / 6.8
        Mx.translation = Vector((math.cos(a) * rr * 1.12, y, math.sin(a) * rr)) + nrm * h / 2
        bmesh.ops.create_cube(bm, size=1.0, matrix=Mx @ Matrix.Diagonal((w, l, h, 1.0)))
    for k in range(10):                                 # ventral tanks
        y = -2.2 + k * 0.42
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.07, depth=0.34, location=(0.0, y, -0.36), rotation=(math.pi / 2, 0, 0))
        o = bpy.context.active_object; o.data.materials.append(mats['greeble']); parts.append(o)
    parts.append(mesh_from_bm('ms_greeble', bm, mats['greeble'], smooth=False))
    ship = join(parts, 'Ship')
    bpy.context.scene.collection.objects.unlink(ship); coll.objects.link(ship)
    # orange lattice booms (separate object, parented)
    lines = []
    for sx in (-1, 1):
        x0, z0, w = sx * 0.58, 0.0, 0.075
        rails = [(x0 - w, z0 - w * 0.6), (x0 + w, z0 - w * 0.6), (x0, z0 + w)]
        y0, y1, step = -4.3, 3.4, 0.14
        for (rx, rz) in rails:
            lines.append([(rx, y0, rz), (rx, y1, rz)])
        y = y0; k = 0
        while y < y1 - 1e-6:
            yn = min(y + step, y1)
            for i in range(3):
                a, b = rails[i], rails[(i + 1) % 3]
                lines.append([(a[0], y, a[1]), (b[0], yn, b[1])] if k % 2 == 0 else [(b[0], y, b[1]), (a[0], yn, a[1])])
            y = yn; k += 1
        for yy in (-3.6, -2.0, -0.2, 1.6, 3.2):           # struts to the hull
            lines.append([(x0 - sx * w, yy, 0.0), (sx * 0.34, yy, 0.0)])
    booms = curve_obj('ms_booms', lines, 0.008, mats['orange'], res=1)
    coll.objects.link(booms); bpy.context.scene.collection.objects.unlink(booms)
    booms.parent = ship
    foil = []
    for sx in (-1, 1):
        for yy in (-3.6, -2.0, -0.2, 1.6, 3.2):
            bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.10, depth=0.10, location=(sx * 0.58, yy, 0.0), rotation=(math.pi / 2, 0, 0))
            o = bpy.context.active_object; o.data.materials.append(mats['foil']); foil.append(o)
    foil = join(foil, 'ms_foil'); foil.parent = ship
    # habitat ring (rotates about the ship axis)
    ring_parts = []
    ring = lathe('ms_ring', [(0.10, 1.30), (0.10, 1.42), (-0.10, 1.42), (-0.10, 1.30), (0.10, 1.30)], 192, mats['ringwin'], cap=False)
    ring_parts.append(ring)
    for k in range(6):
        a = 2 * math.pi * k / 6
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.05, depth=1.0, location=(0.82 * math.cos(a), 0, 0.82 * math.sin(a)),
                                            rotation=(0, math.pi / 2 - a, 0))
        o = bpy.context.active_object; o.data.materials.append(mats['ringframe']); ring_parts.append(o)
    bm = bmesh.new()
    for k in range(48):
        a = 2 * math.pi * (k + 0.5) / 48
        Mx = Matrix.Rotation(-a, 4, 'Y') @ Matrix.Translation((1.36, 0, 0)) @ Matrix.Diagonal((0.10, 0.26, 0.17, 1.0))
        bmesh.ops.create_cube(bm, size=1.0, matrix=Mx)
    ring_parts.append(mesh_from_bm('ms_ringmods', bm, mats['ringframe'], smooth=False))
    hub = lathe('ms_hub', [(0.16, 0.0), (0.16, 0.42), (-0.16, 0.42), (-0.16, 0.0)], 64, mats['ringframe'])
    ring_parts.append(hub)
    ringobj = join(ring_parts, 'HabRing')
    ringobj.location = (0, 1.0, 0); ringobj.parent = ship
    # plumes: nested cones, Generated Y runs nozzle -> tail
    plumes = []
    for sx in (-1, 1):
        for (r0, r1, ln) in ((0.13, 0.03, 1.5), (0.17, 0.08, 2.1)):
            prof = [(0.0, r0), (-ln * 0.15, r0 * 1.05), (-ln * 0.6, (r0 + r1) / 2), (-ln, r1)]
            pl = lathe(f'ms_plume{sx}', prof, 48, mats['plume'], cap=False)
            pl.location = (sx * 0.33, -4.70, 0); pl.parent = ship
            pl.visible_shadow = False
            plumes.append(pl)
    return dict(ship=ship, ring=ringobj, plumes=plumes, coll=coll)

def build_shuttle(mats):
    parts = []
    s = lathe('sh_body', [(0.06, 0.0), (0.05, 0.012), (0.0, 0.016), (-0.05, 0.016), (-0.06, 0.012)], 16, mats['shuttle'])
    parts.append(s)
    bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=12, radius=0.010)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, -0.061, 0))
    parts.append(mesh_from_bm('sh_glow', bm, mats['core'], smooth=False))
    pl = lathe('sh_plume', [(-0.061, 0.009), (-0.10, 0.007), (-0.20, 0.0)], 12, mats['plume'], cap=False)
    parts.append(pl)
    sh = join(parts, 'Shuttle')
    return sh

# ----------------------------------------------------------------------------- world, lights, render
def world_stars(strength=5.0):
    w = bpy.data.worlds.new('Space'); bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld')
    tc = N(nt, 'ShaderNodeTexCoord')
    vor = N(nt, 'ShaderNodeTexVoronoi', Scale=700.0); L(nt, tc.outputs['Generated'], vor.inputs['Vector'])
    star = M(nt, 'LESS_THAN', vor.outputs['Distance'], 0.04)
    sep = N(nt, 'ShaderNodeSeparateColor'); L(nt, vor.outputs['Color'], sep.inputs[0])
    b = M(nt, 'MULTIPLY', star, M(nt, 'POWER', sep.outputs['Red'], 4.0))
    bg = N(nt, 'ShaderNodeBackground', Color=(0.9, 0.93, 1.0, 1)); L(nt, M(nt, 'MULTIPLY', b, strength), bg.inputs['Strength'])
    lp = N(nt, 'ShaderNodeLightPath'); blk = N(nt, 'ShaderNodeBackground', Color=(0.02, 0.025, 0.035, 1), Strength=0.05)
    mx = N(nt, 'ShaderNodeMixShader'); L(nt, lp.outputs['Is Camera Ray'], mx.inputs['Fac'])
    L(nt, blk.outputs[0], mx.inputs[1]); L(nt, bg.outputs[0], mx.inputs[2]); L(nt, mx.outputs[0], out.inputs['Surface'])

def lights():
    key = bpy.data.lights.new('Key', 'SUN'); key.energy = 5.0; key.angle = math.radians(0.6); key.color = (1.0, 0.82, 0.6)
    k = link(bpy.data.objects.new('Key', key)); k.rotation_euler = Vector((-0.92, 0.2, -0.33)).to_track_quat('-Z', 'Y').to_euler()
    fl = bpy.data.lights.new('Fill', 'SUN'); fl.energy = 0.9; fl.color = (0.6, 0.72, 1.0)
    fo = link(bpy.data.objects.new('Fill', fl)); fo.rotation_euler = Vector((-0.8, 0.5, 0.3)).to_track_quat('-Z', 'Y').to_euler()
    rim = bpy.data.lights.new('Rim', 'SUN'); rim.energy = 1.4; rim.color = (0.55, 0.7, 1.0)
    r = link(bpy.data.objects.new('Rim', rim)); r.rotation_euler = Vector((0.3, -0.6, -0.8)).to_track_quat('-Z', 'Y').to_euler()

def setup_render(samples, res=(1080, 1620), nf=96):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for dev_type in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = dev_type; prefs.get_devices(); ok = False
            for dv in prefs.devices:
                dv.use = (dv.type == dev_type); ok = ok or dv.use
            if ok:
                break
        except Exception as ex:
            print('[dev]', dev_type, ex)
    sc.cycles.device = 'GPU'; sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPTIX'
    except Exception:
        pass
    sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 24; sc.cycles.sample_clamp_indirect = 8.0
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5
    sc.frame_start, sc.frame_end = 1, nf
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception:
        pass
    sc.view_settings.exposure = -0.3
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
    tree = bpy.data.node_groups.new('Comp', 'CompositorNodeTree'); sc.compositing_node_group = tree; sc.render.use_compositing = True
    tree.interface.new_socket(name='Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    rl = tree.nodes.new('CompositorNodeRLayers'); outn = tree.nodes.new('NodeGroupOutput')
    g = tree.nodes.new('CompositorNodeGlare')
    for k, v in (('Type', 'Bloom'), ('Quality', 'High'), ('Threshold', 1.1), ('Strength', 0.22), ('Size', 0.75)):
        try:
            g.inputs[k].default_value = v
        except Exception as e:
            print('[comp]', k, e)
    tree.links.new(rl.outputs['Image'], g.inputs['Image']); tree.links.new(g.outputs['Image'], outn.inputs[0])

def build_all():
    reset()
    mats = dict(hull=mat_hull(), rib=mat_metal('MS_Rib', (0.20, 0.21, 0.23), 0.4), orange=mat_metal('MS_Orange', (0.95, 0.30, 0.06), 0.45, 0.6),
                foil=mat_foil(), ringwin=mat_ringwin(), ringframe=mat_metal('MS_RingFrame', (0.55, 0.43, 0.26), 0.3),
                core=mat_emit('MS_Core', (0.55, 0.8, 1.0), 14.0), bridge=mat_emit('MS_BridgeWin', (1.0, 0.7, 0.38), 4.0),
                hangar=mat_emit('MS_Hangar', (1.0, 0.72, 0.42), 3.0), plume=mat_plume(),
                shuttle=mat_metal('SH_Body', (0.62, 0.64, 0.67), 0.3, 0.7), greeble=mat_metal('MS_Greeble', (0.30, 0.31, 0.33), 0.45, 0.6))
    ship = build_ship(mats)
    world_stars(); lights()
    return mats, ship

# ----------------------------------------------------------------------------- shots
def look(cam, pos, target, roll_up):
    fwd = (target - pos).normalized(); rgt = fwd.cross(roll_up).normalized(); up = rgt.cross(fwd)
    cam.location = pos; cam.rotation_euler = Matrix((rgt, up, -fwd)).transposed().to_euler()

def look_axis(cam, pos, target, axis_a, axis_b, screen_deg):
    """aim at target, then roll so the projection of axis_a->axis_b points at screen_deg (0 = right, 90 = up)"""
    fwd = (target - pos).normalized(); up0 = Vector((0, 0, 1))
    rgt = fwd.cross(up0).normalized(); up = rgt.cross(fwd)
    def proj(p):
        d = p - pos; z = d.dot(fwd); return Vector((d.dot(rgt) / z, d.dot(up) / z))
    v = proj(axis_b) - proj(axis_a)
    roll = math.atan2(v.y, v.x) - math.radians(screen_deg)
    q = Matrix.Rotation(-roll, 3, fwd)
    rgt, up = q @ rgt, q @ up
    cam.location = pos; cam.rotation_euler = Matrix((rgt, up, -fwd)).transposed().to_euler()

def shot_s01(mats, ship, nf=58):
    """01: from low behind-right, engines near bottom-left, nose far top-right, ring mid-frame.
    The ship glides forward through the frame, the ring turns, shuttles cross."""
    sc = bpy.context.scene
    s = ship['ship']
    cd = bpy.data.cameras.new('Cam'); cd.lens = 27; cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36; cd.clip_start = 0.05; cd.clip_end = 5000
    cam = link(bpy.data.objects.new('Cam', cd)); sc.camera = cam
    for f in range(1, nf + 1):
        t = (f - 1) / (nf - 1)
        s.location = Vector((0.0, -0.5 + 1.0 * t, 0.0)); s.keyframe_insert('location', frame=f)
        ship['ring'].rotation_euler = (0, math.radians(-14 * t * nf / FPS), 0); ship['ring'].keyframe_insert('rotation_euler', frame=f)
        pos = Vector((5.3 - 0.25 * t, -5.0 + 0.3 * t, -1.6 + 0.06 * t))
        look_axis(cam, pos, Vector((0.0, -1.9, 0.0)), s.location + Vector((0, -4.7, 0)), s.location + Vector((0, 5.0, 0)), 62.0)
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
        for n in (nd for nd in mats['plume'].node_tree.nodes if nd.name == 'PlumeW'):
            n.outputs[0].default_value = f * 0.12; n.outputs[0].keyframe_insert('default_value', frame=f)
    sh = build_shuttle(mats)
    paths = [((4.0, -4.6, -1.3), (1.5, 0.6, -0.5), 3.2), ((1.0, -3.2, -0.55), (0.85, 2.6, -0.45), 2.0), ((2.6, -6.2, -0.9), (1.2, -2.8, -0.5), 2.4)]
    for i, (a0, b0, scl) in enumerate(paths):
        o = sh if i == 0 else sh.copy()
        if i:
            link(o)
        o.scale = (scl, scl, scl)
        a0, b0 = Vector(a0), Vector(b0)
        o.rotation_euler = (b0 - a0).to_track_quat('Y', 'Z').to_euler()
        for f in (1, nf):
            t = (f - 1) / (nf - 1)
            o.location = a0.lerp(b0, t); o.keyframe_insert('location', frame=f)
    return cam

def _cam(lens=30):
    cd = bpy.data.cameras.new('Cam'); cd.lens = lens; cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36
    cd.clip_start = 0.02; cd.clip_end = 5000
    cam = link(bpy.data.objects.new('Cam', cd)); bpy.context.scene.camera = cam
    return cam

def _plume_anim(mats, f, gain):
    for nd in mats['plume'].node_tree.nodes:
        if nd.name == 'PlumeW':
            nd.outputs[0].default_value = f * 0.12; nd.outputs[0].keyframe_insert('default_value', frame=f)
        if nd.name == 'PlumeGain':
            nd.outputs[0].default_value = gain; nd.outputs[0].keyframe_insert('default_value', frame=f)
    em = mats['core'].node_tree.nodes.get('Emit')
    if em:
        em.inputs['Strength'].default_value = 2.0 + 16.0 * gain; em.inputs['Strength'].keyframe_insert('default_value', frame=f)

def shot_s05(mats, ship, nf=48):
    """05: close behind the twin nozzles, cores light up and the plumes ignite toward camera-left, slight shake."""
    cam = _cam(30)
    ship['ring'].rotation_euler = (0, 0, 0)
    for f in range(1, nf + 1):
        t = (f - 1) / (nf - 1)
        ig = min(1.0, max(0.0, (t - 0.12) / 0.35)); ig = ig * ig * (3 - 2 * ig)
        _plume_anim(mats, f, 0.05 + 1.25 * ig)
        sh = 0.006 * ig * math.sin(f * 2.3) + 0.004 * ig * math.sin(f * 3.7 + 1.0)
        pos = Vector((1.05 + sh, -6.15 - 0.2 * t, 0.85 + sh))
        look_axis(cam, pos, Vector((0.0, -4.6, 0.05)), Vector((0, -4.7, 0)), Vector((0, 5.0, 0)), 75.0)
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
        ship['ship'].location = Vector((0, 0.0 + 0.6 * t * t, 0)); ship['ship'].keyframe_insert('location', frame=f)
    return cam

def shot_sprite(mats, ship):
    """transparent side view: nose up-left (heading into image 1's hub), plumes on"""
    sc = bpy.context.scene; sc.render.film_transparent = True
    cam = _cam(50)
    _plume_anim(mats, 1, 1.0)
    pos = Vector((-15.0, -3.0, 3.2))
    look_axis(cam, pos, Vector((0.0, -0.4, 0.0)), Vector((0, -4.7, 0)), Vector((0, 5.0, 0)), 150.0)
    return cam

def shot_shsprite(mats, ship):
    """transparent shuttle, side view, nose to the right and slightly down (leaving the hangar)"""
    sc = bpy.context.scene; sc.render.film_transparent = True
    ship['coll'].hide_render = True
    for o in ship['coll'].all_objects:
        o.hide_render = True
    for o in bpy.context.scene.objects:
        if o.type == 'MESH':
            o.hide_render = True
    sh = build_shuttle(mats); sh.location = (0, 0, 0)
    cam = _cam(50)
    look_axis(cam, Vector((-0.55, -0.12, 0.18)), Vector((0, 0, 0)), Vector((0, -0.06, 0)), Vector((0, 0.06, 0)), -12.0)
    return cam

if __name__ == '__main__':
    samples = int(arg('--samples', 32)); pct = int(arg('--pct', 50))
    mats, ship = build_all()
    nf = 64
    shot = arg('--shot', 's01')
    if shot == 's01':
        shot_s01(mats, ship, nf)
    elif shot == 's05':
        nf = 48; shot_s05(mats, ship, nf)
    elif shot == 'sprite':
        nf = 1; shot_sprite(mats, ship)
    elif shot == 'shsprite':
        nf = 1; shot_shsprite(mats, ship)
    setup_render(samples, nf=nf, res=(1600, 900) if shot in ('sprite', 'shsprite') else (1080, 1620))
    sc = bpy.context.scene; sc.render.resolution_percentage = pct
    if shot in ('sprite', 'shsprite'):
        sc.render.image_settings.color_mode = 'RGBA'
    stills = arg('--stills')
    if stills:
        os.makedirs(os.path.join(HERE, 'tests'), exist_ok=True)
        tag = arg('--tag', 'm1')
        for f in [int(v) for v in str(stills).split(',')]:
            sc.frame_set(f)
            sc.render.filepath = os.path.join(HERE, 'tests', f'ms_{shot}_{tag}_f{f:04d}.png')
            bpy.ops.render.render(write_still=True)
    if arg('--anim'):
        outdir = os.path.join(HERE, 'renders', f'ms_{shot}'); os.makedirs(outdir, exist_ok=True)
        sc.render.filepath = os.path.join(outdir, ''); bpy.ops.render.render(animation=True)
