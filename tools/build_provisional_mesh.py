#!/usr/bin/env python3
"""色分け領域(regions.json)と部材定義(object-map.json)から、暫定の3DメッシュをOBJ+MTLで書き出す。

使い方: python3 tools/build_provisional_mesh.py <regions.json> <object-map.json> <出力ディレクトリ> [--scale 0.353] [--cell 1.0] [--no-flip-x]

- 座標: 東=+X, 北=+Z, 上=+Y(メートル)。原点=番所の重心。OBJはUnity取り込み時にXが反転するため、既定で X=-東 として出力する
  (Unityで 東=+X になる)。鏡像になっていたら --no-flip-x で作り直す。
- 土塁は +高さ、堀は -深さ の高さ場を作り、3x3平滑化で斜面を付ける(断面の根拠はなく、形はあくまで仮)。
- 虎口は土塁に幅4mの通路を切り(平滑化の後で床を0mに戻す)、土橋は堀を切らずに残した帯として表す。
- 建物(番所・火薬庫・箱番所)・虎口の石積み・冠木門・木柵は、箱と切妻屋根の単純な立体。
- MTL は根拠区分で色分け: C橙(位置は推定/断面はB), U灰青(断面が未確認), D赤紫(視覚補完)。
- 縮尺 --scale は docs/scale-calibration.md の値(0.353 m/px, ±3%)。
依存: Pillow, numpy
"""
import argparse, csv, json, math, os
import numpy as np
from PIL import Image, ImageDraw

MATS = {'ground': (0.80, 0.78, 0.72), 'earth_C': (0.95, 0.65, 0.15), 'moat_C': (0.25, 0.55, 0.85), 'moat_U': (0.55, 0.62, 0.70),
        'earth_U': (0.70, 0.70, 0.70), 'bridge_D': (0.85, 0.45, 0.60), 'obj_D': (0.75, 0.30, 0.45)}


def nearest(comps, color, c, tol=60):
    best, bd = None, 1e9
    for r in comps.get(color, []):
        d = math.hypot(r['centroid_px'][0] - c[0], r['centroid_px'][1] - c[1])
        if d < bd: best, bd = r, d
    return best if bd <= tol else None


def blur(h, n):
    for _ in range(n):
        p = np.pad(h, 1, mode='edge')
        h = sum(p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    return h


def unit(bearing_deg):
    """方位角(北=0, 東=90)の単位ベクトルを (東, 北) で返す"""
    b = math.radians(bearing_deg)
    return (math.sin(b), math.cos(b))


def rect(c, u, v, hu, hv):
    """中心c(東,北)、軸u・v(単位ベクトル)、半長hu・hv の長方形の4隅(東,北)"""
    return [(c[0] + su * hu * u[0] + sv * hv * v[0], c[1] + su * hu * u[1] + sv * hv * v[1]) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


class Solids:
    """凸な立体を集めて、外向き法線になるよう巻き順を整えてOBJに書き出す"""

    def __init__(self, sx): self.items, self.sx = [], sx

    def add(self, name, mat, verts, faces):
        self.items.append((name, mat, verts, faces))

    def box(self, name, mat, c, bearing, length, width, y0, y1):
        u = unit(bearing); v = (u[1], -u[0])
        q = rect(c, u, v, length / 2, width / 2)
        verts = [(p[0], y0, p[1]) for p in q] + [(p[0], y1, p[1]) for p in q]
        self.add(name, mat, verts, [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    def gable(self, name, mat, c, bearing, length, width, y_eave, y_ridge, overhang, south_extra=0.0):
        """切妻屋根(棟は長軸方向)。south_extra: 南側の軒を余分に出す長さ(庇)"""
        u = unit(bearing); v = (u[1], -u[0])
        hu, hv = length / 2 + overhang, width / 2 + overhang
        q = rect(c, u, v, hu, hv)
        verts = [(p[0], y_eave, p[1]) for p in q]
        verts += [(c[0] - u[0] * hu, y_ridge, c[1] - u[1] * hu), (c[0] + u[0] * hu, y_ridge, c[1] + u[1] * hu)]
        self.add(name, mat, verts, [(0, 1, 2, 3), (0, 1, 5, 4), (3, 2, 5, 4), (0, 3, 4), (1, 2, 5)])

    def write(self, f, base):
        for name, mat, verts, faces in self.items:
            f.write(f'o {name}\nusemtl {mat}\n')
            for e, y, n in verts: f.write(f'v {self.sx * e:.2f} {y:.2f} {n:.2f}\n')
            ctr = np.mean([(self.sx * e, y, n) for e, y, n in verts], axis=0)
            for fa in faces:
                pts = np.array([(self.sx * verts[i][0], verts[i][1], verts[i][2]) for i in fa])
                nrm = np.zeros(3)
                for k in range(len(pts)):  # Newell法
                    p, q = pts[k], pts[(k + 1) % len(pts)]
                    nrm += np.array([(p[1] - q[1]) * (p[2] + q[2]), (p[2] - q[2]) * (p[0] + q[0]), (p[0] - q[0]) * (p[1] + q[1])])
                if np.dot(nrm, pts.mean(axis=0) - ctr) < 0: fa = tuple(reversed(fa))
                f.write('f ' + ' '.join(str(base + i + 1) for i in fa) + '\n')
            base += len(verts)
        return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('regions'); ap.add_argument('objmap'); ap.add_argument('outdir')
    ap.add_argument('--scale', type=float, default=0.353); ap.add_argument('--cell', type=float, default=1.0)
    ap.add_argument('--no-flip-x', action='store_true'); ap.add_argument('--smooth', type=int, default=2)
    a = ap.parse_args()
    reg = json.load(open(a.regions, encoding='utf-8')); cfg = json.load(open(a.objmap, encoding='utf-8'))
    ox, oy = reg['origin_px']; s = a.scale; cell = a.cell
    tom = lambda p: ((p[0] - ox) * s, -(p[1] - oy) * s)  # (東, 北)
    comps = reg['regions']
    placed, missing = [], []
    for o in cfg['areas']:
        r = nearest(comps, o['color'], o['centroid_px'])
        (placed if r else missing).append((o, r))
    xs = [tom(p)[0] for _, r in placed for p in r['polygon_px']]; ys = [tom(p)[1] for _, r in placed for p in r['polygon_px']]
    margin = 25.0
    xmin, xmax, ymin, ymax = min(xs) - margin, max(xs) + margin, min(ys) - margin, max(ys) + margin
    nx, ny = int((xmax - xmin) / cell) + 1, int((ymax - ymin) / cell) + 1
    earth = np.zeros((ny, nx)); moat = np.zeros((ny, nx)); owner = np.full((ny, nx), -1, int)
    ledger = []
    ij = lambda e, n: ((e - xmin) / cell, (ymax - n) / cell)

    def raster(poly_en):
        im = Image.new('L', (nx, ny), 0)
        ImageDraw.Draw(im).polygon([ij(*p) for p in poly_en], fill=1)
        return np.array(im, bool)

    for k, (o, r) in enumerate(placed):
        m = raster([tom(p) for p in r['polygon_px']])
        if o['kind'] == 'earthwork': earth[m] = np.maximum(earth[m], o['height_m']); owner[m] = k
        else: moat[m] = np.maximum(moat[m], o['depth_m']); owner[m & (owner < 0)] = k
        ledger.append({'id': o['id'], 'name': o['name'], 'kind': o['kind'], 'spec_no': o.get('spec_no'), 'plan_evidence': o['plan_evidence'],
                       'section_evidence': o['section_evidence'], 'height_m': o.get('height_m', ''), 'depth_m': o.get('depth_m', ''),
                       'plan_area_m2': round(r['area_px'] * s * s, 1), 'centroid_east_m': round(tom(r['centroid_px'])[0], 1),
                       'centroid_north_m': round(tom(r['centroid_px'])[1], 1), 'note': o.get('note', '')})
    raw = np.where(earth > 0, earth, -moat)
    H = blur(raw, a.smooth)
    cat = np.zeros((ny, nx), int)  # 0 ground, 1 earth_C, 2 moat_C, 3 moat_U, 4 earth_U, 5 bridge_D
    for k, (o, r) in enumerate(placed):
        mm = owner == k
        cat[mm] = (4 if o['section_evidence'] == 'U' else 1) if o['kind'] == 'earthwork' else (3 if o['section_evidence'] == 'U' else 2)

    # --- 虎口(通路を切る)と土橋(堀を残した帯)。平滑化の後で床を0mに戻す ---
    solids = Solids(1.0 if a.no_flip_x else -1.0)
    gates = {g['id']: g for g in cfg.get('gates', [])}
    gate_c = {}
    for g in gates.values():
        c = tom(g['px']); gate_c[g['id']] = c
        out = unit(g['outward_bearing_deg']); v = (out[1], -out[0])
        passage = rect(c, out, v, g['through_m'] / 2 + 1.0, g['width_m'] / 2)
        H[raster(passage)] = 0.0
        # 冠木門: 柱2本+冠木(通路の長さ方向の中央)
        for sgn in (-1, 1):
            pc = (c[0] + sgn * v[0] * (g['width_m'] / 2 + 0.15), c[1] + sgn * v[1] * (g['width_m'] / 2 + 0.15))
            solids.box(f"{g['id']}_post{'L' if sgn < 0 else 'R'}", 'obj_D', pc, g['outward_bearing_deg'], 0.3, 0.3, 0.0, g['gate_h_m'])
        solids.box(f"{g['id']}_beam", 'obj_D', c, g['outward_bearing_deg'], 0.3, g['width_m'] + 0.9, g['gate_h_m'] - 0.25, g['gate_h_m'] + 0.05)
        if g.get('stone_h_m', 0) > 0:  # 通路の両側の間知石積み(高さ1.9m・通路方向に through_m)
            for sgn in (-1, 1):
                wc = (c[0] + sgn * v[0] * (g['width_m'] / 2 + 0.3), c[1] + sgn * v[1] * (g['width_m'] / 2 + 0.3))
                solids.box(f"{g['id']}_stone{'L' if sgn < 0 else 'R'}", 'obj_D', wc, g['outward_bearing_deg'], g['through_m'], 0.6, 0.0, g['stone_h_m'])
        if g.get('fence_each_side_m', 0) > 0:  # 木柵(両翼)
            fl = g['fence_each_side_m']
            for sgn in (-1, 1):
                off = g['width_m'] / 2 + 0.6 + fl / 2
                fc = (c[0] + sgn * v[0] * off, c[1] + sgn * v[1] * off)
                solids.box(f"{g['id']}_fence{'L' if sgn < 0 else 'R'}", 'obj_D', fc, g['outward_bearing_deg'] + 90, fl, 0.12, 0.0, 1.8)
        ledger.append({'id': g['id'], 'name': g['name'], 'kind': 'gate', 'spec_no': g['spec_no'], 'plan_evidence': g['plan_evidence'],
                       'section_evidence': g['section_evidence'], 'height_m': g['gate_h_m'], 'depth_m': '', 'plan_area_m2': round(g['width_m'] * g['through_m'], 1),
                       'centroid_east_m': round(c[0], 1), 'centroid_north_m': round(c[1], 1), 'note': g.get('note', '')})
    for b in cfg.get('bridges', []):
        g = gates[b['gate']]; c = gate_c[g['id']]
        out = unit(g['outward_bearing_deg']); v = (out[1], -out[0])
        dist = g['through_m'] / 2 + b['length_m'] / 2
        bc = (c[0] + out[0] * dist, c[1] + out[1] * dist)
        m = raster(rect(bc, out, v, b['length_m'] / 2, b['width_m'] / 2))
        H[m] = 0.0; cat[m] = 5
        ledger.append({'id': b['id'], 'name': b['name'], 'kind': 'bridge', 'spec_no': b['spec_no'], 'plan_evidence': b['plan_evidence'],
                       'section_evidence': b['section_evidence'], 'height_m': b['height_m'], 'depth_m': '', 'plan_area_m2': round(b['width_m'] * b['length_m'], 1),
                       'centroid_east_m': round(bc[0], 1), 'centroid_north_m': round(bc[1], 1), 'note': b.get('note', '')})

    # --- 建物 ---
    ground = lambda e, n: float(H[min(max(int((ymax - n) / cell), 0), ny - 1), min(max(int((e - xmin) / cell), 0), nx - 1)])
    for o in cfg['buildings']:
        r = nearest(comps, 'orange', o['centroid_px'], 80) if o.get('use_orange') else None
        c = tom(r['centroid_px'] if r else o['centroid_px'])
        gy = max(ground(*c), 0.0)
        solids.box(o['id'] + '_walls', 'obj_D', c, o['bearing_deg'], o['length_m'], o['width_m'], gy, gy + o['eave_h_m'])
        if o['ridge_h_m'] > o['eave_h_m']:
            solids.gable(o['id'] + '_roof', 'obj_D', c, o['bearing_deg'], o['length_m'], o['width_m'], gy + o['eave_h_m'], gy + o['ridge_h_m'], o.get('overhang_m', 0.3))
        if o.get('eave_south_m'):  # 南側の庇: 薄い板と柱2本
            u = unit(o['bearing_deg']); ec = (c[0], c[1] - (o['width_m'] / 2 + o['eave_south_m'] / 2))
            solids.box(o['id'] + '_eave', 'obj_D', ec, 90, o['length_m'], o['eave_south_m'], gy + o['eave_h_m'] - 0.1, gy + o['eave_h_m'])
            for sgn in (-1, 1):
                solids.box(f"{o['id']}_eavepost{sgn}", 'obj_D', (c[0] + sgn * (o['length_m'] / 2 - 0.2), c[1] - (o['width_m'] / 2 + o['eave_south_m'] - 0.2)), 0, 0.15, 0.15, gy, gy + o['eave_h_m'] - 0.1)
        ledger.append({'id': o['id'], 'name': o['name'], 'kind': 'building', 'spec_no': o.get('spec_no'), 'plan_evidence': o['plan_evidence'],
                       'section_evidence': o['section_evidence'], 'height_m': o['ridge_h_m'], 'depth_m': '', 'plan_area_m2': round(o['length_m'] * o['width_m'], 1),
                       'centroid_east_m': round(c[0], 1), 'centroid_north_m': round(c[1], 1), 'note': o.get('note', '')})

    sx = solids.sx
    X = sx * (xmin + np.arange(nx) * cell); Z = ymax - np.arange(ny) * cell
    os.makedirs(a.outdir, exist_ok=True)
    names = ['ground', 'earth_C', 'moat_C', 'moat_U', 'earth_U', 'bridge_D']
    faces = {n: [] for n in names}
    vid = lambda i, j: j * nx + i + 1
    for j in range(ny - 1):
        for i in range(nx - 1):
            c4 = cat[j:j + 2, i:i + 2].ravel()
            pr = [x for x in (5, 1, 4, 2, 3) if x in c4]  # 土橋>土塁>堀
            n = names[pr[0]] if pr else 'ground'
            a_, b_, c_, d_ = vid(i, j), vid(i + 1, j), vid(i, j + 1), vid(i + 1, j + 1)
            faces[n] += [(a_, c_, b_), (b_, c_, d_)] if sx > 0 else [(a_, b_, c_), (b_, d_, c_)]
    with open(os.path.join(a.outdir, 'kuzuha_provisional.mtl'), 'w') as f:
        for n, col in MATS.items(): f.write(f'newmtl {n}\nKd {col[0]} {col[1]} {col[2]}\n')
    with open(os.path.join(a.outdir, 'kuzuha_provisional.obj'), 'w') as f:
        f.write('# 楠葉台場 暫定メッシュ(縮尺・形状は仮。根拠区分で色分け)\nmtllib kuzuha_provisional.mtl\no site_terrain\n')
        for j in range(ny):
            for i in range(nx): f.write(f'v {X[i]:.2f} {H[j, i]:.2f} {Z[j]:.2f}\n')
        for n in names:
            if faces[n]:
                f.write(f'usemtl {n}\n')
                for t in faces[n]: f.write(f'f {t[0]} {t[1]} {t[2]}\n')
        solids.write(f, nx * ny)
    with open(os.path.join(a.outdir, 'object-ledger.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ledger[0].keys())); w.writeheader(); w.writerows(ledger)
    ev = float(np.clip(H, 0, None).sum() * cell * cell); mv = float(np.clip(-H, 0, None).sum() * cell * cell)
    st = {'scale_m_per_px': s, 'cell_m': cell, 'grid': [nx, ny], 'extent_m': {'east': [xmin, xmax], 'north': [ymin, ymax]},
          'earth_volume_m3_heightfield': round(ev), 'moat_volume_m3_heightfield': round(mv), 'unmatched': [o['id'] for o, _ in missing],
          'flip_x': sx < 0, 'solids': len(solids.items)}
    json.dump(st, open(os.path.join(a.outdir, 'mesh-stats.json'), 'w'), ensure_ascii=False, indent=1)
    col = np.zeros((ny, nx, 3)); col[:] = (200, 198, 190)
    col[cat == 1] = (240, 165, 40); col[cat == 4] = (180, 180, 180); col[cat == 2] = (60, 140, 215); col[cat == 3] = (140, 158, 178); col[cat == 5] = (215, 110, 150)
    gy_, gx_ = np.gradient(H); shade = np.clip(0.75 + 0.9 * (gx_ - gy_) * 0.4, 0.45, 1.15)
    Image.fromarray(np.clip(col * shade[..., None], 0, 255).astype(np.uint8)).resize((nx * 2, ny * 2), Image.NEAREST).save(os.path.join(a.outdir, 'preview_topdown.png'))
    print(json.dumps(st, ensure_ascii=False))


if __name__ == '__main__':
    main()
