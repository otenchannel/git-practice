#!/usr/bin/env python3
"""手彩色の地形図から、直線の輪郭(ベクトル図形)で土塁・堀・虎口・土橋・建物の3D(OBJ+MTL+テクスチャ)を作る。

従来の build_provisional_mesh.py(格子の高さ場)とは別の方式。
  1. 彩色領域の帯から中心線を取り(骨格化)、直線に簡略化する。
  2. 帯の幅は整備案の寸法で固定する(両側の縁が平行な、角のはっきりした直線の図形になる)。
  3. 土塁・堀の足元(foot)と頂部/底(crest)の直線を「守る線」として、制約付き三角形分割(Triangle)で地形を作る。
     辺そのものが直線になり、格子のギザギザが出ない。三角形も約1/10に減る。
  4. 虎口は土塁に幅4mの通路を切り、土橋は堀を切り残す。どちらも図形の引き算で作る。
  5. 色・テクスチャも同じ図形から描く(境界は直線)。

使い方:
  python3 tools/build_vector_mesh.py <regions.json> <object-map.json> <出力ディレクトリ> --dem <dem.npy> --dem-meta <meta.txt> --origin <緯度,経度>
         [--scale 0.353] [--datum-m 5.0] [--plan-only] [--photo <写真.jpg>]
座標: 東=+X, 北=+Z, 上=+Y(m)。OBJはUnity取り込み時にXが反転するため X=-東 で出力する(--no-flip-x で無効)。
依存: numpy, Pillow, shapely, triangle, scikit-image, networkx(pip install shapely triangle scikit-image networkx)
"""
import argparse, csv, importlib.util, json, math, os, sys
import numpy as np
import shapely
import networkx as nx
import triangle as tr
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union
from skimage.morphology import skeletonize

_spec = importlib.util.spec_from_file_location('legacy', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build_provisional_mesh.py'))
L = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(L)
Solids, NAT, MATS, nat_mat, unit, rect, nearest, dem_base = L.Solids, L.NAT, L.MATS, L.nat_mat, L.unit, L.rect, L.nearest, L.dem_base
BUF = dict(cap_style='flat', join_style='mitre', mitre_limit=4.0)


def biggest(g):
    if g.is_empty: return g
    if g.geom_type == 'MultiPolygon': return max(g.geoms, key=lambda p: p.area)
    return g


def spine_of(poly_xy, res=0.25, simplify=1.2):
    """帯状の領域の中心線(骨格の最長経路)を、直線に簡略化して返す。両端は領域の端まで延ばす"""
    P = biggest(Polygon(poly_xy).buffer(0))
    e0, n0, e1, n1 = P.bounds; e0 -= 2; n0 -= 2; e1 += 2; n1 += 2
    w, h = int((e1 - e0) / res) + 1, int((n1 - n0) / res) + 1
    im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).polygon([((x - e0) / res, (n1 - y) / res) for x, y in P.exterior.coords], fill=1)
    ys, xs = np.nonzero(skeletonize(np.array(im, bool))); pts = set(zip(ys.tolist(), xs.tolist())); G = nx.Graph()
    for (y, x) in pts:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dy or dx) and (y + dy, x + dx) in pts: G.add_edge((y, x), (y + dy, x + dx), weight=math.hypot(dy, dx))
    comp = max(nx.connected_components(G), key=len); Hh = G.subgraph(comp)
    d = nx.single_source_dijkstra_path_length(Hh, next(iter(comp))); b = max(d, key=d.get)
    d2, paths = nx.single_source_dijkstra(Hh, b); c = max(d2, key=d2.get)
    ls = LineString([(e0 + x * res, n1 - y * res) for y, x in paths[c]]).simplify(simplify)
    co = [np.array(p) for p in ls.coords]
    for end, nb in ((0, 1), (-1, -2)):
        r = P.exterior.distance(Point(co[end])); v = co[end] - co[nb]; v = v / (np.linalg.norm(v) or 1)
        co[end] = co[end] + v * r
    return LineString([tuple(p) for p in co]), P


def snap_polyline(ls, families_deg, tol_deg, max_move=3.0):
    """各線分を、基準の向き(方位, 度)の系統に近ければその向きへ揃え、頂点を隣り合う線の交点で作り直す"""
    c = [np.array(p, float) for p in ls.coords]
    if len(c) < 2: return ls
    lines = []  # (通る点, 単位方向)
    for a_, b_ in zip(c, c[1:]):
        d = b_ - a_; L_ = np.linalg.norm(d)
        if L_ < 1e-9: continue
        br = math.degrees(math.atan2(d[0], d[1])) % 180
        best = min(families_deg, key=lambda f: min(abs(br - f % 180), 180 - abs(br - f % 180)))
        diff = min(abs(br - best % 180), 180 - abs(br - best % 180))
        if diff <= tol_deg:
            u = np.array([math.sin(math.radians(best)), math.cos(math.radians(best))])
            if np.dot(u, d) < 0: u = -u
        else: u = d / L_
        lines.append(((a_ + b_) / 2, u))
    def proj(p, line): m, u = line; return m + u * np.dot(p - m, u)
    out = [proj(c[0], lines[0])]
    for k in range(1, len(lines)):
        (m0, u0), (m1, u1) = lines[k - 1], lines[k]
        A = np.array([[u0[0], -u1[0]], [u0[1], -u1[1]]]); det = np.linalg.det(A)
        orig = c[k]
        if abs(det) > 0.1:
            t = np.linalg.solve(A, m1 - m0); q = m0 + u0 * t[0]
            if np.linalg.norm(q - orig) > max_move: q = (proj(orig, lines[k - 1]) + proj(orig, lines[k])) / 2
        else: q = (proj(orig, lines[k - 1]) + proj(orig, lines[k])) / 2
        out.append(q)
    out.append(proj(c[-1], lines[-1]))
    return LineString([tuple(p) for p in out])


class Feature:
    def __init__(self, o, foot, crest, level):
        self.o, self.foot, self.crest, self.level = o, foot, crest, level  # level: 土塁なら+高さ、堀なら+深さ(正の値)


def build_features(cfg, comps, tom):
    earth, moat = [], []
    fr = cfg.get('plan_frame')
    fam = [(fr['axis_deg'] + o_) % 180 for o_ in fr['families_offsets_deg']] if fr else None
    snap = (lambda ls: snap_polyline(ls, fam, fr['snap_tol_deg'])) if fr else (lambda ls: ls)
    for o in cfg['areas']:
        mode = o.get('plan_mode', 'skip')
        if mode == 'skip': continue
        r = nearest(comps, o['color'], o['centroid_px'])
        if r is None: continue
        poly = [tom(p) for p in r['polygon_px']]
        if o['kind'] == 'earthwork':
            h = o['height_m']; bw = o['base_width_m']; run = min(1.5 * h, (bw - 0.8) / 2); cw = bw - 2 * run
            if mode == 'strip':
                sp, _ = spine_of(poly, simplify=2.0); sp = snap(sp); foot = sp.buffer(bw / 2, **BUF); crest = sp.buffer(cw / 2, **BUF)
            elif mode == 'rect':
                P = Polygon(poly).buffer(0); mrr = P.minimum_rotated_rectangle; c = mrr.exterior.coords
                e1, e2 = np.array(c[1]) - np.array(c[0]), np.array(c[2]) - np.array(c[1])
                lng, sht = (e1, e2) if np.linalg.norm(e1) >= np.linalg.norm(e2) else (e2, e1)
                ang = math.degrees(math.atan2(lng[1], lng[0])); Lm, Wm = o['rect_size_m']
                ctr = P.centroid; base = affinity.rotate(box(-Lm / 2, -Wm / 2, Lm / 2, Wm / 2), ang, origin=(0, 0))
                foot = affinity.translate(base, ctr.x, ctr.y)
                crest = affinity.translate(affinity.rotate(box(-max(Lm / 2 - run, .3), -max(Wm / 2 - run, .3), max(Lm / 2 - run, .3), max(Wm / 2 - run, .3)), ang, origin=(0, 0)), ctr.x, ctr.y)
            else:  # 'poly'
                foot = biggest(Polygon(poly).buffer(0)).simplify(1.0).buffer(o.get('widen_m', 0), join_style='mitre')
                crest = foot.buffer(-run, join_style='mitre')
                if crest.is_empty: crest = foot.centroid.buffer(0.3)
            earth.append(Feature(o, foot, crest, h))
        else:
            d = o['depth_m']; tw = o.get('top_width_m', 0); run = o.get('wall_run_m', d)  # 既定は勾配1:1
            bwid = max(tw - 2 * run, 0.6)
            if mode == 'strip':
                sp, _ = spine_of(poly, simplify=2.0); sp = snap(sp); foot = sp.buffer(tw / 2, **BUF); crest = sp.buffer(bwid / 2, **BUF)
            else:
                foot = biggest(Polygon(poly).buffer(0)).simplify(1.5); crest = foot.buffer(-min(run, 3.0), join_style='mitre')
                if crest.is_empty: crest = foot.centroid.buffer(0.3)
            moat.append(Feature(o, foot, crest, d))
    return earth, moat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('regions'); ap.add_argument('objmap'); ap.add_argument('outdir')
    ap.add_argument('--scale', type=float, default=0.353); ap.add_argument('--no-flip-x', action='store_true')
    ap.add_argument('--dem'); ap.add_argument('--dem-meta'); ap.add_argument('--origin'); ap.add_argument('--datum-m', type=float, default=5.0)
    ap.add_argument('--dem-sigma-m', type=float, default=12.0); ap.add_argument('--skirt-depth', type=float, default=3.0)
    ap.add_argument('--tex-res', type=float, default=0.15); ap.add_argument('--steiner-m', type=float, default=6.0); ap.add_argument('--margin-m', type=float, default=30.0)
    ap.add_argument('--plan-only', action='store_true', help='図形を作って写真に重ねた確認画像だけ出す'); ap.add_argument('--photo')
    a = ap.parse_args()
    reg = json.load(open(a.regions, encoding='utf-8')); cfg = json.load(open(a.objmap, encoding='utf-8'))
    ox, oy = reg['origin_px']; s = a.scale; comps = reg['regions']
    adj = cfg.get('plan_adjust', {}); rot = math.radians(adj.get('rotate_deg', 0.0)); sh = (adj.get('shift_e_m', 0.0), adj.get('shift_n_m', 0.0))

    def tom(p):  # 写真px -> (東, 北)[m]。plan_adjust(東端の辺に合わせた回転・平行移動)を反映
        e, n = (p[0] - ox) * s, -(p[1] - oy) * s
        return (e * math.cos(rot) - n * math.sin(rot) + sh[0], e * math.sin(rot) + n * math.cos(rot) + sh[1])
    fromm = lambda e, n: (ox + ((e - sh[0]) * math.cos(rot) + (n - sh[1]) * math.sin(rot)) / s, oy - (-(e - sh[0]) * math.sin(rot) + (n - sh[1]) * math.cos(rot)) / s)

    earth, moat = build_features(cfg, comps, tom)
    # --- 虎口の通路と土橋の長方形(図形) ---
    gates = {g['id']: g for g in cfg.get('gates', [])}; passages = {}; bridges = []
    for g in gates.values():
        c = tom(g['px']); out = unit(g['outward_bearing_deg'] + (0)); v = (out[1], -out[0])
        passages[g['id']] = Polygon(rect(c, out, v, g['through_m'] / 2 + 1.0, g['width_m'] / 2))
    for b in cfg.get('bridges', []):
        g = gates[b['gate']]; c = tom(g['px']); out = unit(g['outward_bearing_deg']); v = (out[1], -out[0])
        bc = (c[0] + out[0] * (g['through_m'] / 2 + b['length_m'] / 2), c[1] + out[1] * (g['through_m'] / 2 + b['length_m'] / 2))
        bridges.append((b, Polygon(rect(bc, out, v, b['length_m'] / 2, b['width_m'] / 2))))
    pas_u = unary_union(list(passages.values())) if passages else None
    for f in earth:  # 通路を切る(切り口は法面になる)
        if pas_u is not None and f.foot.intersects(pas_u):
            f.foot = f.foot.difference(pas_u); f.crest = f.crest.difference(pas_u.buffer(max(f.level * 1.0, 1.0), join_style='mitre'))
    bank_u = unary_union([f.foot for f in earth])
    br_u = unary_union([p for _, p in bridges]) if bridges else None
    for f in moat:  # 堀は土塁の足元を超えない/土橋は切り残す
        f.foot = f.foot.difference(bank_u)
        if br_u is not None:
            f.foot = f.foot.difference(br_u); f.crest = f.crest.difference(br_u.buffer(1.0, join_style='mitre'))
        f.crest = f.crest.intersection(f.foot)
    earth = [f for f in earth if not f.foot.is_empty]; moat = [f for f in moat if not f.foot.is_empty]
    print('土塁の図形 %d / 堀の図形 %d / 虎口 %d / 土橋 %d' % (len(earth), len(moat), len(passages), len(bridges)))

    if a.plan_only or True:  # 確認用: 写真に直線の輪郭を重ねる
        ph = a.photo or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data/raw/terrain/20261014_hirakata_map_overlay.jpg')
        if os.path.exists(ph):
            im = Image.open(ph).convert('RGB'); d = ImageDraw.Draw(im)
            def draw(g, col, w=2):
                for pg in (g.geoms if hasattr(g, 'geoms') else [g]):
                    if pg.is_empty or pg.geom_type != 'Polygon': continue
                    for ring in [pg.exterior] + list(pg.interiors): d.line([fromm(*p) for p in ring.coords], fill=col, width=w)
            for f in moat: draw(f.foot, (0, 90, 255)); draw(f.crest, (0, 200, 255), 1)
            for f in earth: draw(f.foot, (255, 120, 0)); draw(f.crest, (255, 0, 0), 1)
            for p in passages.values(): draw(p, (255, 0, 255), 2)
            for _, p in bridges: draw(p, (0, 160, 0), 2)
            x0, y0, x1, y1 = 300, 880, 1060, 1760
            os.makedirs(a.outdir, exist_ok=True); im.crop((x0, y0, x1, y1)).save(os.path.join(a.outdir, 'plan_overlay.png'))
    if a.plan_only: return
    build_mesh(a, cfg, comps, tom, earth, moat, passages, bridges, gates, s)


def build_mesh(a, cfg, comps, tom, earth, moat, passages, bridges, gates, s):
    sx = 1.0 if a.no_flip_x else -1.0
    allg = [f.foot for f in earth + moat]
    e0, n0, e1, n1 = unary_union(allg).bounds
    xmin, xmax, ymin, ymax = e0 - a.margin_m, e1 + a.margin_m, n0 - a.margin_m, n1 + a.margin_m
    # --- 土台の標高(DEMを平滑化して、Y=0=基準面にずらす)。2mの粗い格子で作り、双一次補間で引く ---
    cell2 = 2.0; nx2, ny2 = int((xmax - xmin) / cell2) + 2, int((ymax - ymin) / cell2) + 2
    B2 = dem_base(a, xmin, ymax, nx2, ny2, cell2) - a.datum_m if a.dem else np.zeros((ny2, nx2))

    def base_at(E, N):
        E, N = np.atleast_1d(E).astype(float), np.atleast_1d(N).astype(float)
        fx = np.clip((E - xmin) / cell2, 0, nx2 - 1.001); fy = np.clip((ymax - N) / cell2, 0, ny2 - 1.001)
        i, j = fx.astype(int), fy.astype(int); aa, bb = fx - i, fy - j
        return B2[j, i] * (1 - aa) * (1 - bb) + B2[j, i + 1] * aa * (1 - bb) + B2[j + 1, i] * (1 - aa) * bb + B2[j + 1, i + 1] * aa * bb

    def relief(xy):
        pts = shapely.points(xy); R = np.zeros(len(xy)); M = np.zeros(len(xy))
        for feats, acc in ((earth, R), (moat, M)):
            for f in feats:
                idx = np.nonzero(shapely.intersects(f.foot, pts))[0]
                if not len(idx): continue
                dF = shapely.distance(f.foot.boundary, pts[idx]); dC = shapely.distance(f.crest, pts[idx])
                acc[idx] = np.maximum(acc[idx], f.level * dF / np.maximum(dF + dC, 1e-9))
        return np.where(M > 1e-9, -M, R)

    # --- 制約付き三角形分割: 足元・頂部の直線を「守る線」にする ---
    rectb = LineString([(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax), (xmin, ymin)])
    lines = [rectb] + [g.boundary for f in earth + moat for g in (f.foot, f.crest) if not g.is_empty]
    noded = shapely.segmentize(unary_union(lines), 12.0)
    segs, key = [], {}
    verts = []

    def vid(p):
        k = (round(p[0], 5), round(p[1], 5))
        if k not in key: key[k] = len(verts); verts.append(k)
        return key[k]
    for g in (noded.geoms if hasattr(noded, 'geoms') else [noded]):
        c = list(g.coords)
        for p, q in zip(c, c[1:]):
            i, j = vid(p), vid(q)
            if i != j: segs.append((i, j))
    n_feat = len(verts)
    gx_, gy_ = np.meshgrid(np.arange(xmin + a.steiner_m / 2, xmax, a.steiner_m), np.arange(ymin + a.steiner_m / 2, ymax, a.steiner_m))
    sp_ = np.stack([gx_.ravel(), gy_.ravel()], 1)
    far = shapely.distance(noded, shapely.points(sp_)) > 2.5
    for p in sp_[far]: vid(tuple(p))
    V = np.array(verts)
    T = tr.triangulate({'vertices': V, 'segments': np.array(segs)}, 'p')
    Vt, tris = T['vertices'], T['triangles']
    rel = relief(Vt); Ht = base_at(Vt[:, 0], Vt[:, 1]) + rel
    # 向き: 書き出し座標(X=sx*東)の外積が上向きになる巻き順
    P3 = np.stack([sx * Vt[:, 0], Ht, Vt[:, 1]], 1)
    nrm = np.cross(P3[tris[:, 1]] - P3[tris[:, 0]], P3[tris[:, 2]] - P3[tris[:, 0]])
    flip = nrm[:, 1] < 0; tris[flip] = tris[flip][:, [0, 2, 1]]
    nrm = np.cross(P3[tris[:, 1]] - P3[tris[:, 0]], P3[tris[:, 2]] - P3[tris[:, 0]]); nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    assert (nrm[:, 1] > 0).all(), '地面の面に下向きが残っている'
    # 法線: 地形の土台だけの滑らかな面(格子の差分)を頂点法線に、特徴(足元・頂部)に触れる面は平らな法線(角をはっきりさせる)
    dE = (base_at(Vt[:, 0] + 1, Vt[:, 1]) - base_at(Vt[:, 0] - 1, Vt[:, 1])) / 2; dN = (base_at(Vt[:, 0], Vt[:, 1] + 1) - base_at(Vt[:, 0], Vt[:, 1] - 1)) / 2
    vnrm = np.stack([sx * (-dE), np.ones(len(Vt)), -dN], 1); vnrm /= np.linalg.norm(vnrm, axis=1, keepdims=True)
    is_feat_v = np.zeros(len(Vt), bool); is_feat_v[:n_feat] = True
    feat_face = (np.abs(rel[tris]).max(axis=1) > 1e-6) | is_feat_v[tris].any(axis=1)
    print('頂点 %d / 三角形 %d(土台 %d, 特徴に触れる %d)' % (len(Vt), len(tris), (~feat_face).sum(), feat_face.sum()))

    solids = Solids(sx, lambda e, n: float(base_at(e, n)[0]))
    ledger = []
    ground_rel = lambda e, n: max(float(relief(np.array([[e, n]]))[0]), 0.0)
    wb = cfg.get('wells_bearing_deg', 90)
    # 虎口: 冠木門・石積み・木柵
    for g in gates.values():
        c = tom(g['px']); out = unit(g['outward_bearing_deg']); v = (out[1], -out[0])
        for sgn in (-1, 1):
            pc = (c[0] + sgn * v[0] * (g['width_m'] / 2 + 0.15), c[1] + sgn * v[1] * (g['width_m'] / 2 + 0.15))
            solids.box(f"{g['id']}_post{'L' if sgn < 0 else 'R'}", 'obj_D', pc, g['outward_bearing_deg'], 0.3, 0.3, 0.0, g['gate_h_m'])
        solids.box(f"{g['id']}_beam", 'obj_D', c, g['outward_bearing_deg'], 0.3, g['width_m'] + 0.9, g['gate_h_m'] - 0.25, g['gate_h_m'] + 0.05)
        if g.get('stone_h_m', 0) > 0:
            for sgn in (-1, 1):
                wc = (c[0] + sgn * v[0] * (g['width_m'] / 2 + 0.3), c[1] + sgn * v[1] * (g['width_m'] / 2 + 0.3))
                solids.box(f"{g['id']}_stone{'L' if sgn < 0 else 'R'}", 'obj_D', wc, g['outward_bearing_deg'], g['through_m'], 0.6, 0.0, g['stone_h_m'])
        if g.get('fence_each_side_m', 0) > 0:
            fl = g['fence_each_side_m']
            for sgn in (-1, 1):
                off = g['width_m'] / 2 + 0.6 + fl / 2; fc = (c[0] + sgn * v[0] * off, c[1] + sgn * v[1] * off)
                solids.box(f"{g['id']}_fence{'L' if sgn < 0 else 'R'}", 'obj_D', fc, g['outward_bearing_deg'] + 90, fl, 0.12, 0.0, 1.8)
        ledger.append({'id': g['id'], 'name': g['name'], 'kind': g.get('kind', 'gate'), 'spec_no': g['spec_no'], 'plan_evidence': g['plan_evidence'],
                       'section_evidence': g['section_evidence'], 'height_m': g['gate_h_m'], 'depth_m': '', 'plan_area_m2': round(g['width_m'] * g['through_m'], 1),
                       'centroid_east_m': round(c[0], 1), 'centroid_north_m': round(c[1], 1), 'note': g.get('note', '')})
    for b, poly in bridges:
        c = poly.centroid
        ledger.append({'id': b['id'], 'name': b['name'], 'kind': 'bridge', 'spec_no': b['spec_no'], 'plan_evidence': b['plan_evidence'],
                       'section_evidence': b['section_evidence'], 'height_m': b['height_m'], 'depth_m': '', 'plan_area_m2': round(poly.area, 1),
                       'centroid_east_m': round(c.x, 1), 'centroid_north_m': round(c.y, 1), 'note': b.get('note', '')})
    for o in cfg['buildings']:
        r = nearest(comps, 'orange', o['centroid_px'], 80) if o.get('use_orange') else None
        c = tom(r['centroid_px'] if r else o['centroid_px']); gy = ground_rel(*c)
        solids.box(o['id'] + '_walls', 'obj_D', c, o['bearing_deg'], o['length_m'], o['width_m'], gy, gy + o['eave_h_m'])
        if o['ridge_h_m'] > o['eave_h_m']:
            solids.gable(o['id'] + '_roof', 'obj_D', c, o['bearing_deg'], o['length_m'], o['width_m'], gy + o['eave_h_m'], gy + o['ridge_h_m'], o.get('overhang_m', 0.3))
        if o.get('eave_south_m'):
            ub = unit(o['bearing_deg']); vb = (ub[1], -ub[0])  # 庇は棟の直角方向(右手側の反対=南寄り)
            sgn = -1 if vb[1] > 0 else 1
            ec = (c[0] + sgn * vb[0] * (o['width_m'] / 2 + o['eave_south_m'] / 2), c[1] + sgn * vb[1] * (o['width_m'] / 2 + o['eave_south_m'] / 2))
            solids.box(o['id'] + '_eave', 'obj_D', ec, o['bearing_deg'], o['length_m'], o['eave_south_m'], gy + o['eave_h_m'] - 0.1, gy + o['eave_h_m'])
            for sg in (-1, 1):
                pp = (c[0] + ub[0] * sg * (o['length_m'] / 2 - 0.2) + sgn * vb[0] * (o['width_m'] / 2 + o['eave_south_m'] - 0.2), c[1] + ub[1] * sg * (o['length_m'] / 2 - 0.2) + sgn * vb[1] * (o['width_m'] / 2 + o['eave_south_m'] - 0.2))
                solids.box(f"{o['id']}_eavepost{sg}", 'obj_D', pp, 0, 0.15, 0.15, gy, gy + o['eave_h_m'] - 0.1)
        ledger.append({'id': o['id'], 'name': o['name'], 'kind': 'building', 'spec_no': o.get('spec_no'), 'plan_evidence': o['plan_evidence'],
                       'section_evidence': o['section_evidence'], 'height_m': o['ridge_h_m'], 'depth_m': '', 'plan_area_m2': round(o['length_m'] * o['width_m'], 1),
                       'centroid_east_m': round(c[0], 1), 'centroid_north_m': round(c[1], 1), 'note': o.get('note', '')})
    for w in cfg.get('wells', []):
        c = tom(w['px']); gy = ground_rel(*c); h = w['house_m']
        for sx_ in (-1, 1):
            for sz_ in (-1, 1):
                u = unit(wb); vv = (u[1], -u[0])
                pc = (c[0] + sx_ * u[0] * (h / 2 - 0.1) + sz_ * vv[0] * (h / 2 - 0.1), c[1] + sx_ * u[1] * (h / 2 - 0.1) + sz_ * vv[1] * (h / 2 - 0.1))
                solids.box(f"{w['id']}_post{sx_}{sz_}", 'obj_D', pc, 0, 0.15, 0.15, gy, gy + w['post_h_m'])
        solids.gable(w['id'] + '_roof', 'obj_D', c, wb, h, h, gy + w['post_h_m'], gy + w['roof_h_m'], 0.25)
        f_ = w['frame_m']; u = unit(wb); vv = (u[1], -u[0])
        for k_, sg in enumerate((1, -1)):
            solids.box(f"{w['id']}_frameA{k_}", 'obj_D', (c[0] + sg * vv[0] * (f_ / 2 - 0.05), c[1] + sg * vv[1] * (f_ / 2 - 0.05)), wb, f_, 0.1, gy, gy + w['frame_h_m'])
            solids.box(f"{w['id']}_frameB{k_}", 'obj_D', (c[0] + sg * u[0] * (f_ / 2 - 0.05), c[1] + sg * u[1] * (f_ / 2 - 0.05)), wb + 90, f_, 0.1, gy, gy + w['frame_h_m'])
        ledger.append({'id': w['id'], 'name': w['name'], 'kind': 'well', 'spec_no': w['spec_no'], 'plan_evidence': w['plan_evidence'],
                       'section_evidence': w['section_evidence'], 'height_m': w['roof_h_m'], 'depth_m': '', 'plan_area_m2': round(h * h, 1),
                       'centroid_east_m': round(c[0], 1), 'centroid_north_m': round(c[1], 1), 'note': w.get('note', '')})
    for gp in cfg.get('gun_platforms', []):
        c = tom(gp['px']); u = unit(gp['ramp_bearing_deg'])
        solids.box(gp['id'] + '_platform', 'obj_D', c, gp['ramp_bearing_deg'], gp['size_m'], gp['size_m'], 0.0, gp['top_h_m'])
        rc = (c[0] + u[0] * (gp['size_m'] / 2 + gp['ramp_len_m'] / 2), c[1] + u[1] * (gp['size_m'] / 2 + gp['ramp_len_m'] / 2))
        solids.wedge(gp['id'] + '_ramp', 'obj_D', rc, gp['ramp_bearing_deg'] + 180, gp['ramp_len_m'], gp['ramp_w_m'], gp['top_h_m'])
        ledger.append({'id': gp['id'], 'name': gp['name'], 'kind': 'gun_platform', 'spec_no': gp['spec_no'], 'plan_evidence': gp['plan_evidence'],
                       'section_evidence': gp['section_evidence'], 'height_m': gp['top_h_m'], 'depth_m': '', 'plan_area_m2': round(gp['size_m'] ** 2 + gp['ramp_len_m'] * gp['ramp_w_m'], 1),
                       'centroid_east_m': round(c[0], 1), 'centroid_north_m': round(c[1], 1), 'note': gp.get('note', '')})
    for f in earth + moat:
        c = f.foot.centroid
        ledger.append({'id': f.o['id'], 'name': f.o['name'], 'kind': f.o['kind'], 'spec_no': f.o.get('spec_no'), 'plan_evidence': f.o['plan_evidence'],
                       'section_evidence': f.o['section_evidence'], 'height_m': f.o.get('height_m', ''), 'depth_m': f.o.get('depth_m', ''),
                       'plan_area_m2': round(f.foot.area, 1), 'centroid_east_m': round(c.x, 1), 'centroid_north_m': round(c.y, 1), 'note': f.o.get('note', '')})
    # --- 土台(外周の壁と底面) ---
    ring = [tuple(map(float, p)) for p in rectb.segmentize(12.0).coords][:-1]
    # 外周頂点を、三角形分割の頂点と同じ高さにそろえる(外周は制約線なので必ず頂点がある)
    kmap = {(round(p[0], 5), round(p[1], 5)): i for i, p in enumerate(Vt)}
    rv = []
    for p in ring:
        i = kmap.get((round(p[0], 5), round(p[1], 5)))
        rv.append((p[0], float(Ht[i]) if i is not None else float(base_at(p[0], p[1])[0]), p[1]))
    if a.skirt_depth > 0:
        m_ = len(rv); sv = rv + [(p[0], -a.skirt_depth, p[2]) for p in rv]
        sf = [(k, (k + 1) % m_, m_ + (k + 1) % m_, m_ + k) for k in range(m_)] + [tuple(range(m_, 2 * m_))]
        solids.add('site_base', 'ground', sv, sf, absolute=True)
    # --- 地面テクスチャ(直線の図形を高解像度で描く) ---
    res = a.tex_res; tw, th = int((xmax - xmin) / res), int((ymax - ymin) / res)
    px = lambda p: ((p[0] - xmin) / res, (ymax - p[1]) / res)

    def paint(img, g, col, hole=None):
        d = ImageDraw.Draw(img)
        for pg in (g.geoms if hasattr(g, 'geoms') else [g]):
            if pg.is_empty or pg.geom_type != 'Polygon': continue
            d.polygon([px(p) for p in pg.exterior.coords], fill=col)
            for r_ in pg.interiors: d.polygon([px(p) for p in r_.coords], fill=hole if hole is not None else col)
    rng = np.random.default_rng(7)

    def bil(A, fx, fy):
        fx = np.clip(fx, 0, A.shape[1] - 1.001); fy = np.clip(fy, 0, A.shape[0] - 1.001)
        i, j = fx.astype(int), fy.astype(int); aa, bb = fx - i, fy - j
        return A[j, i] * (1 - aa) * (1 - bb) + A[j, i + 1] * aa * (1 - bb) + A[j + 1, i] * (1 - aa) * bb + A[j + 1, i + 1] * aa * bb

    def vnoise(scale_m, amp):
        gw, gh = int(tw * res / scale_m) + 3, int(th * res / scale_m) + 3
        gg = rng.random((gh, gw)); X_, Y_ = np.meshgrid(np.arange(tw) * res / scale_m, np.arange(th) * res / scale_m)
        return (bil(gg, X_, Y_) - 0.5) * amp
    gcol, ocol = (204, 200, 190), (240, 165, 40)
    ev = Image.new('RGB', (tw, th), gcol)
    for f in moat: paint(ev, f.foot, (60, 140, 215) if f.o['section_evidence'] != 'U' else (140, 158, 178), hole=gcol)
    for f in earth: paint(ev, f.foot, ocol if f.o['section_evidence'] != 'U' else (180, 180, 180), hole=gcol)
    for _, p in bridges: paint(ev, p, (215, 110, 150))
    nat = Image.new('RGB', (tw, th), (104, 130, 70)); soil, mud, dirt, grass = (112, 88, 62), (84, 74, 52), (150, 124, 92), (104, 130, 70)
    for f in moat: paint(nat, f.foot, soil, hole=grass); paint(nat, f.crest, mud, hole=soil)
    for f in earth: paint(nat, f.foot, soil, hole=grass); paint(nat, f.crest, grass, hole=soil)
    for p in passages.values(): paint(nat, p, dirt)
    for _, p in bridges: paint(nat, p, dirt)
    arr = np.array(nat).astype(float) * (1 + (vnoise(6, 0.10) + vnoise(1.5, 0.08) + vnoise(0.4, 0.05))[..., None])
    tex = {'kuzuha_provisional': ev, 'kuzuha_natural': Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))}
    os.makedirs(a.outdir, exist_ok=True)
    for k_, im_ in tex.items(): im_.save(os.path.join(a.outdir, k_ + '_terrain.png'))
    # --- OBJ ---
    MATS['ev_terrain'] = (1.0, 1.0, 1.0); NAT['nat_terrain'] = (1.0, 1.0, 1.0)

    def emit(prefix, comment, mats, terrain_mat, solid_mat_fn):
        with open(os.path.join(a.outdir, prefix + '.mtl'), 'w') as f:
            for n, col in mats.items():
                f.write(f'newmtl {n}\nKd {col[0]} {col[1]} {col[2]}\n')
                if n == terrain_mat: f.write(f'map_Kd {prefix}_terrain.png\n')
        nv = len(Vt)
        with open(os.path.join(a.outdir, prefix + '.obj'), 'w') as f:
            f.write(f'# 楠葉台場 暫定メッシュ(直線の図形から作成: {comment})\nmtllib {prefix}.mtl\no site_terrain\ng site_terrain\n')
            for p, h in zip(Vt, Ht): f.write(f'v {sx * p[0]:.3f} {h:.3f} {p[1]:.3f}\n')
            for p in Vt: f.write(f'vt {(p[0] - xmin) / (xmax - xmin):.5f} {(p[1] - ymin) / (ymax - ymin):.5f}\n')
            for q in vnrm: f.write(f'vn {q[0]:.3f} {q[1]:.3f} {q[2]:.3f}\n')
            for q in nrm[feat_face]: f.write(f'vn {q[0]:.3f} {q[1]:.3f} {q[2]:.3f}\n')
            f.write(f'usemtl {terrain_mat}\n'); k_ = nv
            for t, ff in zip(tris, feat_face):
                if ff:
                    k_ += 1; f.write('f ' + ' '.join(f'{q + 1}/{q + 1}/{k_}' for q in t) + '\n')
                else: f.write('f ' + ' '.join(f'{q + 1}/{q + 1}/{q + 1}' for q in t) + '\n')
            solids.write(f, nv, solid_mat_fn)
    emit('kuzuha_provisional', '根拠区分で色分け', MATS, 'ev_terrain', None)
    emit('kuzuha_natural', '自然な色', NAT, 'nat_terrain', nat_mat)
    for r_ in ledger:
        r_['ground_tp_m'] = round(float(base_at(r_['centroid_east_m'], r_['centroid_north_m'])[0]) + a.datum_m, 1)
    with open(os.path.join(a.outdir, 'object-ledger.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ledger[0].keys())); w.writeheader(); w.writerows(ledger)
    st = {'scale_m_per_px': s, 'vertices': int(len(Vt)), 'triangles': int(len(tris)), 'solids': len(solids.items), 'datum_tp_m': a.datum_m,
          'extent_m': {'east': [xmin, xmax], 'north': [ymin, ymax]}, 'flip_x': sx < 0, 'plan_adjust': cfg.get('plan_adjust'), 'plan_frame_axis_deg': (cfg.get('plan_frame') or {}).get('axis_deg')}
    json.dump(st, open(os.path.join(a.outdir, 'mesh-stats.json'), 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(st, ensure_ascii=False))


if __name__ == '__main__':
    main()
