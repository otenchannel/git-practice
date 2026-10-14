#!/usr/bin/env python3
"""国土地理院の標高タイル(DEM5A, z15, 約5m格子)を取得して貼り合わせ、numpy配列で保存する。

使い方: python3 tools/fetch_gsi_dem.py <緯度> <経度> <出力ディレクトリ> [--radius 2]
出力: dem5a_z15.npy(標高m。欠測=NaN。水面は欠測になる) と dem_meta.txt("zoom 左上タイルx 左上タイルy")
標高値の復元: x=2^16*R+2^8*G+B; x<2^23 なら x*0.01 m, x=2^23 なら欠測, それ以外は (x-2^24)*0.01 m。
出典: 国土地理院(基盤地図情報数値標高モデル)。利用規約に従い出典を明記すること。
"""
import argparse, io, math, os, urllib.request
import numpy as np
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('lat', type=float); ap.add_argument('lon', type=float); ap.add_argument('outdir'); ap.add_argument('--radius', type=int, default=2)
a = ap.parse_args()
z = 15; n = 2 ** z
fx = (a.lon + 180) / 360 * n; fy = (1 - math.asinh(math.tan(math.radians(a.lat))) / math.pi) / 2 * n
cx, cy, R = int(fx), int(fy), a.radius
D = np.full((256 * (2 * R + 1),) * 2, np.nan)
for dx in range(-R, R + 1):
    for dy in range(-R, R + 1):
        url = f'https://cyberjapandata.gsi.go.jp/xyz/dem5a_png/{z}/{cx + dx}/{cy + dy}.png'
        try:
            p = np.array(Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20).read())).convert('RGB')).astype(np.int64)
        except Exception as e:
            print('取得できず', url, e); continue
        X = p[..., 0] * 65536 + p[..., 1] * 256 + p[..., 2]
        D[(dy + R) * 256:(dy + R + 1) * 256, (dx + R) * 256:(dx + R + 1) * 256] = np.where(X < 2 ** 23, X * 0.01, np.where(X == 2 ** 23, np.nan, (X - 2 ** 24) * 0.01))
os.makedirs(a.outdir, exist_ok=True)
np.save(os.path.join(a.outdir, 'dem5a_z15.npy'), D)
open(os.path.join(a.outdir, 'dem_meta.txt'), 'w').write(f'{z} {cx - R} {cy - R}\n')
print('有効画素 %.1f%%' % (100 * np.isfinite(D).mean()), ' 1画素 = %.2f m' % (40075016.686 * math.cos(math.radians(a.lat)) / n / 256))
