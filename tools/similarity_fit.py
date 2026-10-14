#!/usr/bin/env python3
"""対応点から相似変換(拡大縮小+回転+平行移動)を求め、別の点を移す。構造図の設計図 → 地形図の位置合わせ用。

使い方: python3 tools/similarity_fit.py <pairs.json>
pairs.json: {"pairs": {"名前": [[ax,ay],[bx,by]], ...}, "apply": {"名前": [ax,ay], ...}}
  a=変換元の画像座標, b=変換先の画像座標(どちらも x右・y下のピクセル)。
出力: 倍率、回転(画面上で時計回り+)、各対応点の残差(px)、apply の点の変換結果。依存: numpy
"""
import json, math, sys
import numpy as np

d = json.load(open(sys.argv[1], encoding='utf-8'))
names = list(d['pairs'])
A = np.array([d['pairs'][n][0] for n in names], float); B = np.array([d['pairs'][n][1] for n in names], float)
ma, mb = A.mean(0), B.mean(0); Ac, Bc = A - ma, B - mb
U, S, Vt = np.linalg.svd(Bc.T @ Ac / len(A)); sg = np.sign(np.linalg.det(U @ Vt)); D = np.diag([1, sg])
R = U @ D @ Vt; s = (S * np.diag(D)).sum() / (Ac ** 2).sum() * len(A); t = mb - s * R @ ma
f = lambda p: s * R @ np.asarray(p, float) + t
print(f'倍率 {s:.4f} / 回転 {math.degrees(math.atan2(R[1, 0], R[0, 0])):.1f}度')
for n in names:
    r = f(d['pairs'][n][0]) - np.array(d['pairs'][n][1]); print(f'  残差 {n}: ({r[0]:.1f}, {r[1]:.1f}) px')
for n, p in d.get('apply', {}).items():
    q = f(p); print(f'{n}: ({q[0]:.0f}, {q[1]:.0f})')
