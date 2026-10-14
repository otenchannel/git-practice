# 非公開資料の取り扱いと3Dデータ生成手順

**このリポジトリは公開設定。** 枚方市文化財課から頂いた資料(地形図・構造図・整備概要(案))の画像と、そこから起こしたデータはコミットしない。

## 除外しているもの(`.gitignore`)
- `data/raw/**` … 頂いた資料の写真(置き場: `data/raw/terrain/`)
- `data/private/` … 転記した表・標高点・抽出した領域・生成メッシュ
- `unity/KuzuhaDaiba/Assets/StreamingAssets/private/`

コミットしてよいのは、手順・コード・出典の台帳(提供元と日付のみ)・未確認事項。資料の転載や再配布の可否は市に確認する(Q14, Q17)。リポジトリを非公開にすれば、この制限は緩められる。

## 再生成手順
写真を `data/raw/terrain/` に置いてから実行する(Pillow と numpy が必要)。
```
python3 tools/extract_map_regions.py data/raw/terrain/20261014_hirakata_map_overlay.jpg data/private/geo --scale 0.40
python3 tools/build_provisional_mesh.py data/private/geo/regions.json data/private/geo/object-map.json data/private/geo/mesh --scale 0.40
```
出力: `kuzuha_provisional.obj/.mtl`(暫定メッシュ)、`object-ledger.csv`(部材ごとの根拠区分)、`preview_topdown.png`、`mesh-stats.json`。

## Unityへの取り込み
1. `kuzuha_provisional.obj` と `.mtl` を `Assets/Private/`(gitignore対象にすること)へコピーする。
2. 取り込み後、**東が+X、北が+Z** になっているか確認する(番所は原点付近、南東の稜堡が+X・−Z側)。鏡像になっていたら `--no-flip-x` を付けて再生成する。
3. 材質は根拠区分で色分け済み: 橙=位置は推定(C)・断面は整備案の値(B)、灰青=断面が未確認(U)、赤紫=視覚補完(D)。

## 精度と限界(重要)
- 写真は未補正(台形歪み・折り目あり)。**縮尺は仮値0.40 m/px(±10%)**。次の独立した5つの推定の平均:
  番所の短辺0.38、長辺0.45、見切塁の面積0.42、南大堀の面積0.37、土塁面積0.37。
  **確定には原本の縮尺表記が必要(Q15)。**
- 領域は手彩色の範囲を機械的に抽出したもので、測量線ではない。位置の根拠区分はC止まり。
- 赤の線は凡例がなく意味不明のため、モデルには使っていない。
- 土塁・堀の断面は台形ではなく、領域に高さ・深さを与えて3×3平滑化を2回かけた仮の斜面。
- 堀(西面・北・東)の深さは根拠がなく、1mの仮値(根拠区分U)。
- 地面は平坦と仮定。標高点では台場内が約13.2m、東側が約15.5mで、実際は東が約2m高い。DEMを入手して置き換える。
