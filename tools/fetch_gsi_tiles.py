#!/usr/bin/env python3
"""国土地理院の標準地図タイルを取得して1枚に貼り合わせる(縮尺の実測・位置合わせ用)。

使い方: python3 tools/fetch_gsi_tiles.py <緯度> <経度> <出力ディレクトリ> [--zoom 18] [--radius 2]
出力: mosaic_z<zoom>.png と mosaic_meta.txt("zoom 左上タイルx 左上タイルy")。1ピクセルの長さは
 156543.03392 * cos(緯度) / 2**zoom [m](z18で緯度34.88度なら約0.490 m/px)。
出典: 国土地理院タイル(利用規約に従い、出典を明記して利用すること)。
"""
import argparse, io, math, os, urllib.request
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('lat', type=float); ap.add_argument('lon', type=float); ap.add_argument('outdir')
ap.add_argument('--zoom', type=int, default=18); ap.add_argument('--radius', type=int, default=2)
a = ap.parse_args()
n = 2 ** a.zoom
fx = (a.lon + 180) / 360 * n
fy = (1 - math.asinh(math.tan(math.radians(a.lat))) / math.pi) / 2 * n
cx, cy, R = int(fx), int(fy), a.radius
mos = Image.new('RGB', (256 * (2 * R + 1),) * 2, (255, 255, 255))
for dx in range(-R, R + 1):
    for dy in range(-R, R + 1):
        url = f'https://cyberjapandata.gsi.go.jp/xyz/std/{a.zoom}/{cx + dx}/{cy + dy}.png'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        mos.paste(Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read())).convert('RGB'), ((dx + R) * 256, (dy + R) * 256))
os.makedirs(a.outdir, exist_ok=True)
mos.save(os.path.join(a.outdir, f'mosaic_z{a.zoom}.png'))
open(os.path.join(a.outdir, 'mosaic_meta.txt'), 'w').write(f'{a.zoom} {cx - R} {cy - R}\n')
print('m/px =', round(156543.03392 * math.cos(math.radians(a.lat)) / n, 4), ' 指定点のモザイク内位置 px =', round((fx - (cx - R)) * 256), round((fy - (cy - R)) * 256))
