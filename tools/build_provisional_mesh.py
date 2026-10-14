#!/usr/bin/env python3
"""色分け領域(regions.json)と部材定義(object-map.json)から、暫定の3DメッシュをOBJ+MTLで書き出す。

使い方: python3 tools/build_provisional_mesh.py <regions.json> <object-map.json> <出力ディレクトリ> [--scale 0.40] [--cell 1.0] [--no-flip-x]

- 座標: 東=+X, 北=+Z, 上=+Y(メートル)。原点=番所の重心。OBJはUnity取り込み時にXが反転するため、既定で X=-東 として出力する
  (Unityで 東=+X になる)。鏡像になっていたら --no-flip-x で作り直す。
- 土塁は +高さ、堀は -深さ の高さ場を作り、3x3平滑化で斜面を付ける(断面の根拠はなく、形はあくまで仮)。
- MTL は根拠区分で色分け: C橙(位置は推定/断面はB), U灰青(断面が未確認), D赤紫(視覚補完)。
- 縮尺 --scale は仮値(m/px)。縮尺が確定したら更新して再実行する。
依存: Pillow, numpy
"""
import argparse, csv, json, os
import numpy as np
from PIL import Image, ImageDraw

MATS = {'ground': (0.80, 0.78, 0.72), 'earth_C': (0.95, 0.65, 0.15), 'moat_C': (0.25, 0.55, 0.85), 'moat_U': (0.55, 0.62, 0.70),
        'earth_U': (0.70, 0.70, 0.70), 'bldg_D': (0.75, 0.30, 0.45)}


def nearest(comps, color, c, tol=60):
    best, bd = None, 1e9
    for r in comps.get(color, []):
        d = np.hypot(r['centroid_px'][0] - c[0], r['centroid_px'][1] - c[1])
        if d < bd: best, bd = r, d
    return best if bd <= tol else None


def blur(h, n):
    for _ in range(n):
        p = np.pad(h, 1, mode='edge')
        h = sum(p[1 + dy:p.shape[0] - 1 + dy, 1 + dx:p.shape[1] - 1 + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9.0
    return h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('regions'); ap.add_argument('objmap'); ap.add_argument('outdir')
    ap.add_argument('--scale', type=float, default=0.40); ap.add_argument('--cell', type=float, default=1.0)
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
    for k, (o, r) in enumerate(placed):
        im = Image.new('L', (nx, ny), 0)
        poly = [((tom(p)[0] - xmin) / cell, (ymax - tom(p)[1]) / cell) for p in r['polygon_px']]
        ImageDraw.Draw(im).polygon(poly, fill=1)
        m = np.array(im, bool)
        if o['kind'] == 'earthwork': earth[m] = np.maximum(earth[m], o['height_m']); owner[m] = k
        else: moat[m] = np.maximum(moat[m], o['depth_m']); owner[m & (owner < 0)] = k
        ledger.append({'id': o['id'], 'name': o['name'], 'kind': o['kind'], 'spec_no': o.get('spec_no'), 'plan_evidence': o['plan_evidence'],
                       'section_evidence': o['section_evidence'], 'height_m': o.get('height_m', ''), 'depth_m': o.get('depth_m', ''),
                       'plan_area_m2': round(r['area_px'] * s * s, 1), 'centroid_east_m': round(tom(r['centroid_px'])[0], 1),
                       'centroid_north_m': round(tom(r['centroid_px'])[1], 1), 'note': o.get('note', '')})
    raw = np.where(earth > 0, earth, -moat)
    H = blur(raw, a.smooth)
    # 材質: 頂点ごとに土塁>堀>地面。セルは4頂点の優先順で決める
    cat = np.zeros((ny, nx), int)  # 0 ground, 1 earth_C, 2 moat_C, 3 moat_U, 4 earth_U
    kinds = {k: (o['kind'], o['plan_evidence'], o['section_evidence']) for k, (o, r) in enumerate(placed)}
    for k, (kind, pe, se) in kinds.items():
        mm = owner == k
        cat[mm] = (4 if se == 'U' else 1) if kind == 'earthwork' else (3 if se == 'U' else 2)
    sx = 1.0 if a.no_flip_x else -1.0
    X = sx * (xmin + np.arange(nx) * cell); Z = ymax - np.arange(ny) * cell
    os.makedirs(a.outdir, exist_ok=True)
    names = ['ground', 'earth_C', 'moat_C', 'moat_U', 'earth_U']
    faces = {n: [] for n in names}
    vid = lambda i, j: j * nx + i + 1
    for j in range(ny - 1):
        for i in range(nx - 1):
            c = cat[j:j + 2, i:i + 2].ravel()
            pr = [x for x in (1, 4, 2, 3) if x in c]  # 土塁優先
            n = names[pr[0]] if pr else 'ground'
            a_, b_, c_, d_ = vid(i, j), vid(i + 1, j), vid(i, j + 1), vid(i + 1, j + 1)
            # 上向き法線になる巻き順: (東へ+1, 南へ+1)。X=sx*東
            tri = [(a_, c_, b_), (b_, c_, d_)] if sx > 0 else [(a_, b_, c_), (b_, d_, c_)]
            faces[n] += tri
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
        base = nx * ny
        for o in cfg['buildings']:
            r = nearest(comps, 'orange', o['centroid_px'], 80) if o['id'] == 'banjo' else None
            cx, cz = tom(r['centroid_px'] if r else o['centroid_px'])
            ew, ns, h = o['size_ew_ns_h_m']
            gy = float(H[int((ymax - cz) / cell), int((cx - xmin) / cell)])
            f.write(f"o {o['id']}\nusemtl bldg_D\n")
            pts = [(cx + dx * ew / 2, gy + dy * h, cz + dz * ns / 2) for dy in (0, 1) for dz in (-1, 1) for dx in (-1, 1)]
            for p in pts: f.write(f'v {sx * p[0]:.2f} {p[1]:.2f} {p[2]:.2f}\n')
            q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
            for fa in q:
                v = [base + k + 1 for k in fa]
                # 両面描画に頼らず、反転時は逆順に
                f.write(f'f {v[0]} {v[1]} {v[2]} {v[3]}\n' if sx < 0 else f'f {v[3]} {v[2]} {v[1]} {v[0]}\n')
            base += 8
            ledger.append({'id': o['id'], 'name': o['name'], 'kind': 'building', 'spec_no': o.get('spec_no'), 'plan_evidence': o['plan_evidence'],
                           'section_evidence': o['section_evidence'], 'height_m': h, 'depth_m': '', 'plan_area_m2': round(ew * ns, 1),
                           'centroid_east_m': round(cx, 1), 'centroid_north_m': round(cz, 1), 'note': o.get('note', '')})
    with open(os.path.join(a.outdir, 'object-ledger.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ledger[0].keys())); w.writeheader(); w.writerows(ledger)
    ev = float(np.clip(H, 0, None).sum() * cell * cell); mv = float(np.clip(-H, 0, None).sum() * cell * cell)
    st = {'scale_m_per_px': s, 'cell_m': cell, 'grid': [nx, ny], 'extent_m': {'east': [xmin, xmax], 'north': [ymin, ymax]},
          'earth_volume_m3_heightfield': round(ev), 'moat_volume_m3_heightfield': round(mv), 'unmatched': [o['id'] for o, _ in missing],
          'flip_x': sx < 0}
    json.dump(st, open(os.path.join(a.outdir, 'mesh-stats.json'), 'w'), ensure_ascii=False, indent=1)
    # 確認用プレビュー(上=北, 地面=灰, 土塁=橙, 堀=青, 陰影つき)
    col = np.zeros((ny, nx, 3)); col[:] = (200, 198, 190)
    col[cat == 1] = (240, 165, 40); col[cat == 4] = (180, 180, 180); col[cat == 2] = (60, 140, 215); col[cat == 3] = (140, 158, 178)
    gy, gx = np.gradient(H); shade = np.clip(0.75 + 0.9 * (gx - gy) * 0.4, 0.45, 1.15)
    Image.fromarray(np.clip(col * shade[..., None], 0, 255).astype(np.uint8)).resize((nx * 2, ny * 2), Image.NEAREST).save(os.path.join(a.outdir, 'preview_topdown.png'))
    print(json.dumps(st, ensure_ascii=False))


if __name__ == '__main__':
    main()
