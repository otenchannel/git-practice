#!/usr/bin/env python3
"""OBJ(build_provisional_mesh.py の出力)を斜め上から描画して確認する簡易プレビュー(Pillow+numpy)。

使い方: python3 tools/preview_oblique.py <kuzuha_provisional.obj> <出力.png> <中心の東m> <中心の北m> <半径m> [--az 0] [--el 35] [--flip-x]
 --az: 視点の方位(度)。0=南から北を見る。--flip-x: OBJが X=-東 で書かれている場合に指定(既定のビルド出力は指定する)
"""
import argparse, math
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('obj'); ap.add_argument('out'); ap.add_argument('e', type=float); ap.add_argument('n', type=float); ap.add_argument('r', type=float)
ap.add_argument('--az', type=float, default=0); ap.add_argument('--el', type=float, default=35); ap.add_argument('--flip-x', action='store_true')
ap.add_argument('--ppm', type=float, default=14.0); ap.add_argument('--size', type=int, default=1300)
a = ap.parse_args()
mtl = {}
cur = None
import os
mtl_file = 'kuzuha_provisional.mtl'
for l in open(a.obj, encoding='utf-8'):
    if l.startswith('mtllib'): mtl_file = l.split()[1]; break
for l in open(os.path.join(os.path.dirname(a.obj), mtl_file)):
    t = l.split()
    if t and t[0] == 'newmtl': cur = t[1]
    elif t and t[0] == 'Kd': mtl[cur] = tuple(float(x) for x in t[1:4])
V, tris = [], []
mat = 'ground'
for l in open(a.obj, encoding='utf-8'):
    t = l.split()
    if not t: continue
    if t[0] == 'v': V.append((float(t[1]), float(t[2]), float(t[3])))
    elif t[0] == 'usemtl': mat = t[1]
    elif t[0] == 'f':
        idx = [int(x.split('/')[0]) - 1 for x in t[1:]]
        for k in range(1, len(idx) - 1): tris.append((idx[0], idx[k], idx[k + 1], mat))
V = np.array(V)
if a.flip_x: V[:, 0] = -V[:, 0]  # 東=+X に戻す
E, Y, N = V[:, 0] - a.e, V[:, 1], V[:, 2] - a.n
phi, th = math.radians(a.az), math.radians(a.el)
x1 = E * math.cos(phi) + N * math.sin(phi); d1 = -E * math.sin(phi) + N * math.cos(phi)
sx = x1; sy = Y * math.cos(th) + d1 * math.sin(th); depth = d1 * math.cos(th) - Y * math.sin(th)
sel = [(i, j, k, m) for i, j, k, m in tris if max(abs(E[[i, j, k]]).max(), abs(N[[i, j, k]]).max()) <= a.r]
sel.sort(key=lambda t: -(depth[t[0]] + depth[t[1]] + depth[t[2]]))
W = a.size; im = Image.new('RGB', (W, int(W * 0.7)), (235, 235, 240)); d = ImageDraw.Draw(im)
cx, cy = W / 2, int(W * 0.7) * 0.62
light = np.array([0.4, 0.8, -0.45]); light /= np.linalg.norm(light)
P = np.stack([sx, Y, d1], 1)
for i, j, k, m in sel:
    p = (P[i], P[j], P[k]); nrm = np.cross(p[1] - p[0], p[2] - p[0]); ln = np.linalg.norm(nrm)
    if ln == 0: continue
    nrm = nrm / ln
    if nrm[1] < 0: nrm = -nrm
    sh = 0.55 + 0.45 * max(0.0, float(np.dot(nrm, light)))
    col = tuple(int(255 * c * sh) for c in mtl.get(m, (0.8, 0.8, 0.8)))
    d.polygon([(cx + sx[q] * a.ppm, cy - sy[q] * a.ppm) for q in (i, j, k)], fill=col)
im.save(a.out); print(a.out, len(sel), 'triangles')
