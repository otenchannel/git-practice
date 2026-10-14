#!/usr/bin/env python3
"""手彩色された地図写真から色分け領域を抽出し、多角形(ピクセル座標+仮のメートル座標)をJSONに書き出す。

使い方: python3 tools/extract_map_regions.py <写真.jpg> <出力ディレクトリ> [--scale 0.353]

前提(いずれも仮): 写真は未補正(台形歪み・折り目あり)/ 地図は上が北 / 縮尺は --scale (m/px) で与える。
色の意味は凡例が写っていないため推定: yellow=土塁, blue=堀・河川, green=北東側の土手, orange=番所, red=不明。
依存: Pillow, numpy のみ。
"""
import argparse, json, os
import numpy as np
from PIL import Image

ROI = (300, 880, 1060, 1740)  # x0,y0,x1,y1 (1450x2576 の写真で台場周辺)
NB = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]


def classify(a):
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    V = a.max(-1)
    return {
        'yellow': (R > G - 5) & (G > B + 55) & (R > B + 60),
        'blue': (B > R + 18) & (B >= G - 2) & (V > 110),
        'green': (G > R + 8) & (G > B + 4) & (V > 110),
        'red': (R > G + 35) & (R > B + 35) & (V > 110),
        'orange': (R > G + 25) & (G > B + 25) & (R > B + 55) & (R > 150),
    }


def shift(m, dy, dx):
    o = np.zeros_like(m)
    h, w = m.shape
    o[max(dy, 0):h + min(dy, 0), max(dx, 0):w + min(dx, 0)] = m[max(-dy, 0):h + min(-dy, 0), max(-dx, 0):w + min(-dx, 0)]
    return o


def dilate(m):
    o = m.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= shift(m, dy, dx)
    return o


def erode(m):
    return ~dilate(~m)


def close(m, k):
    for _ in range(k): m = dilate(m)
    for _ in range(k): m = erode(m)
    return m


def label(m):
    h, w = m.shape
    lab = np.zeros((h, w), np.int32)
    n = 0
    for y in range(h):
        for x in range(w):
            if m[y, x] and lab[y, x] == 0:
                n += 1
                st = [(y, x)]
                lab[y, x] = n
                while st:
                    cy, cx = st.pop()
                    for dy, dx in NB:
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and m[ny, nx] and lab[ny, nx] == 0:
                            lab[ny, nx] = n
                            st.append((ny, nx))
    return lab, n


def fill_holes(c):
    pad = np.pad(c, 1)
    h, w = pad.shape
    bg = np.zeros_like(pad)
    st = [(0, 0)]
    bg[0, 0] = True
    while st:
        y, x = st.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not pad[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                st.append((ny, nx))
    return (~bg)[1:-1, 1:-1]


def moore(mask):
    ys, xs = np.nonzero(mask)
    i = np.lexsort((xs, ys))[0]
    start = (int(ys[i]), int(xs[i]))
    h, w = mask.shape
    c, pidx, out, first = start, 6, [start], None
    for _ in range(2_000_000):
        nxt = None
        for k in range(1, 9):
            j = (pidx + k) % 8
            ny, nx = c[0] + NB[j][0], c[1] + NB[j][1]
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx]:
                pj = (pidx + k - 1) % 8
                d = (c[0] + NB[pj][0] - ny, c[1] + NB[pj][1] - nx)
                pidx = NB.index(d)
                nxt = (ny, nx)
                break
        if nxt is None: break
        if first is None: first = nxt
        elif c == start and nxt == first: break
        c = nxt
        out.append(c)
    return out


def rdp(pts, eps):
    pts = np.asarray(pts, float)
    keep = np.zeros(len(pts), bool)
    keep[0] = keep[-1] = True
    st = [(0, len(pts) - 1)]
    while st:
        a, b = st.pop()
        if b <= a + 1: continue
        p, q = pts[a], pts[b]
        d = q - p
        n = np.hypot(*d)
        seg = pts[a + 1:b]
        dist = np.hypot(*(seg - p).T) if n == 0 else np.abs(d[0] * (seg[:, 1] - p[1]) - d[1] * (seg[:, 0] - p[0])) / n
        k = int(np.argmax(dist))
        if dist[k] > eps:
            m = a + 1 + k
            keep[m] = True
            st += [(a, m), (m, b)]
    return pts[keep]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('photo'); ap.add_argument('outdir')
    ap.add_argument('--scale', type=float, default=0.353, help='縮尺 m/px(docs/scale-calibration.md)')
    ap.add_argument('--eps', type=float, default=3.0, help='多角形の簡略化許容誤差 px')
    ap.add_argument('--min-area', type=int, default=150)
    a = ap.parse_args()
    X0, Y0, X1, Y1 = ROI
    im = Image.open(a.photo).convert('RGB')
    arr = np.array(im.crop(ROI)).astype(int)
    masks = classify(arr)
    close_k = {'yellow': 2, 'blue': 3, 'green': 2, 'red': 1, 'orange': 1}
    comps, orange_c = {}, None
    for name, m in masks.items():
        m = close(m, close_k[name])
        lab, n = label(m)
        res = []
        for i in range(1, n + 1):
            c = lab == i
            area = int(c.sum())
            if area < a.min_area: continue
            ys, xs = np.nonzero(c)
            filled = fill_holes(c)
            poly = rdp([(x, y) for y, x in moore(filled)], a.eps)
            res.append({'area_px': area, 'bbox_px': [int(xs.min()) + X0, int(ys.min()) + Y0, int(xs.max()) + X0, int(ys.max()) + Y0],
                        'centroid_px': [float(xs.mean()) + X0, float(ys.mean()) + Y0],
                        'polygon_px': [[float(x) + X0, float(y) + Y0] for x, y in poly]})
        comps[name] = res
        if name == 'orange' and res:
            orange_c = max(res, key=lambda r: r['area_px'])['centroid_px']
    ox, oy = orange_c or ((X0 + X1) / 2, (Y0 + Y1) / 2)
    s = a.scale
    for name, res in comps.items():
        for r in res:
            r['area_m2_at_scale'] = round(r['area_px'] * s * s, 1)
            r['polygon_m'] = [[round((x - ox) * s, 2), round(-(y - oy) * s, 2)] for x, y in r['polygon_px']]  # x=東, y=北
    out = {'photo': os.path.basename(a.photo), 'roi_px': list(ROI), 'scale_m_per_px_provisional': s,
           'origin_px': [ox, oy], 'origin_note': '原点=橙領域(番所)の重心。x=東, y=北(上が北と仮定)',
           'assumptions': ['写真は未補正(台形歪み・折り目)', '上が北(「楠葉中之芝」の字が正立, 京阪本線が左=西側)', '色の意味は推定(凡例なし)'],
           'regions': comps}
    os.makedirs(a.outdir, exist_ok=True)
    with open(os.path.join(a.outdir, 'regions.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for k, v in comps.items():
        print(k, len(v), 'components; areas(px):', sorted([r['area_px'] for r in v], reverse=True)[:6])


if __name__ == '__main__':
    main()
