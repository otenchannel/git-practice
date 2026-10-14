#!/usr/bin/env python3
"""DEMの欠測領域(川の水面)の縁の標高から、川の水際の標高(基準面の目安)を推定する。

使い方: python3 tools/estimate_river_datum.py <dem5a_z15.npy> <dem_meta.txt> <緯度> <経度>
レーザー測量は水面の下を測れないので、川底そのものの標高はDEMにない。水際の標高は水位の目安になる。
"""
import math, sys
import numpy as np

D = np.load(sys.argv[1]); z, x0, y0 = map(int, open(sys.argv[2]).read().split()); lat, lon = float(sys.argv[3]), float(sys.argv[4])
n = 2 ** z; mpp = 40075016.686 * math.cos(math.radians(lat)) / n / 256
ox = ((lon + 180) / 360 * n - x0) * 256; oy = ((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n - y0) * 256
valid = np.isfinite(D); inv = ~valid; H, W = inv.shape
lab = np.zeros(inv.shape, int); best = (0, 0); k = 0
for y in range(H):
    for x in range(W):
        if inv[y, x] and not lab[y, x]:
            k += 1; st = [(y, x)]; lab[y, x] = k; c = 0
            while st:
                cy, cx = st.pop(); c += 1
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and inv[ny, nx] and not lab[ny, nx]: lab[ny, nx] = k; st.append((ny, nx))
            if c > best[0]: best = (c, k)
riv = lab == best[1]; p = np.pad(riv, 1); edge = np.zeros_like(riv)
for dy in (-1, 0, 1):
    for dx in (-1, 0, 1):
        if dy or dx: edge |= p[1 + dy:1 + dy + H, 1 + dx:1 + dx + W]
edge &= valid
yy, xx = np.nonzero(edge); dist = np.hypot(xx - ox, yy - oy) * mpp
print('最大の欠測領域(川): %.0f ha' % (best[0] * mpp * mpp / 1e4))
for R in (500, 1000, 2000):
    m = dist < R; v = D[yy[m], xx[m]]
    print('縁の標高 半径%dm: 中央値 %.2f / 下位10%% %.2f / 上位75%% %.2f / 最小 %.2f (n=%d)' % (R, np.median(v), np.percentile(v, 10), np.percentile(v, 75), v.min(), m.sum()))
