# -*- coding: utf-8 -*-
"""中間報告(A4 PDF)を作る。使い方: python3 build_interim_report.py <素材フォルダ> <出力PDF>
素材フォルダに scene_ev.png(根拠色分け)・scene_nat.png(自然色)・game_gate.png・game_far.png・plan.png が必要(非公開データ由来なので git には入れない)。
氏名・学籍番号などは下の META を直す。"""
import os, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, KeepTogether, FrameBreak)
from reportlab.graphics.shapes import Drawing, Rect, String, Line

META = dict(title='幕末期河川台場「楠葉台場」のVR復元と理解促進効果の検証', sub='卒業研究 中間報告', date='2026年11月12日',
            name='(氏名)', sid='(学籍番号)', dept='大阪工業大学 (学部・学科)', adv='指導教員: 平山 亮 先生')
FONT = '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'
pdfmetrics.registerFont(TTFont('JP', FONT))
INK, MUTED, ACC, RULE = colors.HexColor('#1f2933'), colors.HexColor('#5b6770'), colors.HexColor('#1b5e8a'), colors.HexColor('#cfd6dc')
LV = {'A': '#2f8ccf', 'B': '#3fb383', 'C': '#f2a626', 'D': '#c04d73', 'U': '#9a9a9a'}
LVN = {'A': '確認済み', 'B': '史料に記載', 'C': '類例から推定', 'D': '仮説・復元演出', 'U': '資料不足'}

def S(name, **kw):
    base = dict(fontName='JP', fontSize=9.5, leading=15, textColor=INK, alignment=TA_LEFT, wordWrap='CJK')
    base.update(kw); return ParagraphStyle(name, **base)
body, small = S('b'), S('s', fontSize=8, leading=12, textColor=MUTED)
h1 = S('h1', fontSize=14, leading=20, textColor=ACC, spaceBefore=4, spaceAfter=5)
h2 = S('h2', fontSize=10.5, leading=16, textColor=INK, spaceBefore=6, spaceAfter=2)
cell = S('c', fontSize=8.5, leading=12.5); cellb = S('cb', fontSize=8.5, leading=12.5, textColor=colors.white)
bul = S('bul', leftIndent=10, bulletIndent=0, spaceAfter=1.5)
P = lambda t, st=body: Paragraph(t, st)
B = lambda t: Paragraph(t, bul, bulletText='•')

def table(rows, widths, head=True, zebra=True):
    data = [[Paragraph(str(c), cellb if (head and i == 0) else cell) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LINEBELOW', (0, 0), (-1, -1), 0.4, RULE),
          ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]
    if head: st.append(('BACKGROUND', (0, 0), (-1, 0), ACC))
    if zebra:
        for i in range(1, len(rows)):
            if i % 2 == 0: st.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f3f6f8')))
    t.setStyle(TableStyle(st)); return t

def img(path, w):
    from PIL import Image as PI
    iw, ih = PI.open(path).size
    im = Image(path, width=w, height=w * ih / iw); im.hAlign = 'LEFT'; return im

def caption(t): return P(t, small)

def barchart(title, counts, w=82 * mm, h=34 * mm):
    d = Drawing(w, h); mx = max(counts.values()) or 1
    d.add(String(0, h - 8, title, fontName='JP', fontSize=8.5, fillColor=INK))
    y = h - 22
    for k in 'ABCDU':
        v = counts.get(k, 0); bw = (w - 40 * mm) * v / mx
        d.add(String(0, y + 2, f'{k} {LVN[k]}', fontName='JP', fontSize=7.5, fillColor=MUTED))
        d.add(Rect(26 * mm, y, max(bw, 0.5), 5, fillColor=colors.HexColor(LV[k]), strokeColor=None))
        d.add(String(26 * mm + bw + 2, y + 1.5, str(v), fontName='JP', fontSize=7.5, fillColor=INK)); y -= 7
    return d

def build(asset, out):
    A = lambda n: os.path.join(asset, n)
    def deco(c, doc):
        c.saveState(); c.setFont('JP', 7.5); c.setFillColor(MUTED)
        c.drawString(18 * mm, 10 * mm, f'{META["sub"]}  {META["date"]}  {META["name"]}')
        c.drawRightString(A4[0] - 18 * mm, 10 * mm, f'{doc.page}')
        c.drawString(18 * mm, A4[1] - 11 * mm, '学内の中間報告用資料(非公開)。市の提供資料に基づく図を含むため、転載・再配布しないでください。')
        c.setStrokeColor(RULE); c.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm); c.restoreState()
    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
                          title=META['title'] + ' 中間報告', author=META['name'])
    W = A4[0] - 36 * mm
    doc.addPageTemplates([PageTemplate(id='p', frames=[Frame(18 * mm, 20 * mm, W, A4[1] - 38 * mm, id='f', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=deco)])
    s = []
    # ---- 表紙 ----
    s += [Spacer(1, 38 * mm), P(META['sub'], S('t0', fontSize=12, textColor=ACC)), Spacer(1, 4),
          P(META['title'], S('t1', fontSize=21, leading=31)), Spacer(1, 10),
          P('時代考証にもとづく根拠つきの3D復元と、VR体験が空間理解に与える効果の検証', S('t2', fontSize=11, textColor=MUTED)), Spacer(1, 26 * mm)]
    s += [table([['発表日', META['date']], ['所属', META['dept']], ['氏名', f'{META["name"]}(学籍番号 {META["sid"]})'], ['指導', META['adv']]], [28 * mm, W - 28 * mm], head=False, zebra=False), Spacer(1, 14 * mm),
          Spacer(1, 2), img(A('scene_nat.png'), W * 0.6), Spacer(1, 3), caption('図0 試作モデル(自然色版)。Unityで表示した画面。')]
    s += [PageBreak()]
    # ---- 1. 要旨 ----
    s += [P('1. 要旨', h1),
          P('楠葉台場跡(大阪府枚方市、国史跡)は、慶応元年(1865)に完成した、淀川左岸の河川台場である。現地は史跡公園として整備されているが、堀や土塁の配置、番所や虎口などの構造は、現地を歩くだけでは把握しにくい。'
            '本研究は、(1) 時代考証にもとづき、根拠の強さを部材ごとに明示した3D復元をUnityで構築し、(2) その復元を使ったVR体験が、図面・解説資料に比べて空間理解と歴史的関心をどう変えるかを検証する。'),
          P('現在(11月上旬)は、復元モデルとVRアプリの試作(MVP)を、PC上で動かせる段階に達した。資料の入手と倫理審査の確認が、今後の主な課題である。'),
          Spacer(1, 3), P('今回の報告の要点', h2),
          B('<b>進捗:</b> 全体計画(9段階)のうち、資料整理・環境構築・3Dモデル化を終え、Unityでの試作に入った(第3節)'),
          B('<b>成果:</b> 市の提供資料と国土地理院の標高から、縮尺・方位・標高を割り出して位置合わせした、32の要素からなる3Dモデル(第4節)'),
          B('<b>方針:</b> 「どこまでが根拠で、どこからが推定か」を、色と言葉で利用者に見せる。根拠が弱い部分を隠さない(第2節)'),
          B('<b>課題:</b> 発掘報告書・設計図原本の入手、市資料の利用範囲の確認、倫理審査の要否確認(第6節)')]
    # ---- 2. 目的と方法 ----
    s += [P('2. 目的・リサーチクエスチョン・方法', h1),
          table([['RQ1', '根拠レベルを可視化した復元モデルは、どの程度、妥当性を説明できるか'],
                 ['RQ2', 'VR体験は、図面・解説資料に比べて、空間理解と歴史的関心を高めるか']], [14 * mm, W - 14 * mm], head=False),
          Spacer(1, 4), P('時代考証の方法', h2),
          P('考証とは、「何が分かっていて、何が推測か」を出典つきで切り分ける作業である。史料を強さの順に4層に分け、要素ごとに、根拠の強さを5段階で記録する。'),
          Spacer(1, 3),
          table([['層', '例', '使い方'],
                 ['発掘・実測', '発掘調査報告書(枚方市文化財調査報告 第60集)、現存する地割', '位置・規模の根拠(最も強い)'],
                 ['同時代の史料', '設計図(関門絵図)、仕用帳、藩・幕府の記録', '当時の意図・仕様の根拠'],
                 ['現代の整理', '文化庁の解説、案内板、市の整備案、論文', '出典をたどって確認する'],
                 ['類例・現在の地形', '同時期の台場、国土地理院の標高・旧版地図', '資料が無い部分の「推定」の材料']], [30 * mm, 80 * mm, W - 110 * mm]),
          Spacer(1, 4), P('根拠の5段階と、画面での色', h2)]
    lv = Table([[Paragraph(f'<b>{k}</b> {LVN[k]}', S('lv', fontSize=8.5, leading=12, textColor=colors.white, alignment=1)) for k in 'ABCDU']], colWidths=[W / 5] * 5)
    lv.setStyle(TableStyle([('BACKGROUND', (i, 0), (i, 0), colors.HexColor(LV[k])) for i, k in enumerate('ABCDU')] + [('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    s += [lv, Spacer(1, 3), P('A=実測・発掘で確認 / B=史料に明記 / C=類例から推定 / D=視覚的な補完(演出) / U=資料不足のため形を決めない。'
                               '出典は台帳(29件)と未解決の問い(24件)で管理し、資料に当たれていない事項を確定情報として扱わない。', small)]
    # ---- 3. 進捗 ----
    s += [PageBreak(), P('3. 研究の進捗', h1),
          table([['段階', '内容', '期間', '状態'],
                 ['0', '研究設計(題目・RQ・実験案)', '〜10/8', '完了'],
                 ['1', '資料収集・台帳', '10/8〜', '8割(報告書本編・設計図原本は未入手)'],
                 ['2', '開発環境(Unity 6.6 / URP / XR)', '〜10/14', '完了'],
                 ['3', '地形・遺構の3D化', '10/14〜10/31', '<b>ほぼ完了</b>(細部の改善は継続)'],
                 ['4', 'Unity試作(歩行・色分け切替・解説表示)', '10/20〜11/14', '<b>進行中</b>(PCで動作確認済み)'],
                 ['5', '予備実験・実験資料の確定', '11/15〜11/21', '未着手'],
                 ['6', '本実験(各群10名前後)', '11/22〜12/5', '未着手'],
                 ['7', '分析・考察', '12/6〜12/14', '未着手'],
                 ['8', '論文執筆・発表資料・ビルド', '12/15〜12/25', '未着手'],
                 ['9', 'レビュー反映・提出', '12/26〜12/31', '未着手']], [12 * mm, 70 * mm, 28 * mm, W - 110 * mm]),
          Spacer(1, 4), P('ここまでにできたこと', h2),
          B('市の文化財課から提供された資料(彩色地形図・構造図・整備概要(案))を数値化し、国土地理院の地図・標高と突き合わせて、縮尺・方位・標高を決定した(第4節)'),
          B('土塁・堀・虎口・土橋・番所・火薬庫・井戸屋形・大砲台を、位置合わせした地形の上に立体化した'),
          B('根拠の色分け版と自然色版を、Tabキーで切り替えられるUnityアプリを試作した(歩行、クリックで解説を表示)'),
          B('非公開データの管理(公開リポジトリと非公開リポジトリの分離)と、研究室PCへの移行手順を整えた')]
    # ---- 4. 成果 ----
    s += [P('4. 成果: 3Dモデルの構築', h1),
          P('4.1 位置合わせ(縮尺・方位・標高)', h2),
          P('提供された地形図は、縮尺の記載が無いA4の写真で、上が北である。現在も変わらない地物(台場の東辺と京阪線路の距離、南の道路の長さ)を、国土地理院の地図で測り、<b>縮尺を 0.353 m/px(約1/2,300、誤差±3%)</b>と決定した。'
            'Y=0(基準の高さ)は、国土地理院の標高データ(約5mメッシュ)から求めた淀川の水際の標高 <b>5.0 m (T.P.)</b> とした。川底は水面下で測られていないため、水際で代用している(未解決の問いQ24)。')]
    flow = Drawing(W, 17 * mm); xs = [0, 0.26, 0.52, 0.78]; labs = ['写真 → m', '地図・標高に位置合わせ', '輪郭を直線化', '立体化・色付け']
    for x, lab in zip(xs, labs):
        flow.add(Rect(x * W, 3 * mm, 0.21 * W, 11 * mm, fillColor=colors.HexColor('#eaf2f7'), strokeColor=ACC, strokeWidth=0.6))
        flow.add(String(x * W + 0.105 * W, 7.2 * mm, lab, fontName='JP', fontSize=8, fillColor=INK, textAnchor='middle'))
    for x in xs[:-1]:
        flow.add(Line((x + 0.21) * W, 8.5 * mm, (x + 0.26) * W, 8.5 * mm, strokeColor=ACC, strokeWidth=1))
    s += [flow, Spacer(1, 3), KeepTogether([P('4.2 モデルの構成', h2),
          P('手彩色の区画を、整備案の幅・高さと、東端の辺を基準にした向き(方位9.83°とそれに直交・45°の方向)に揃え、直線と一定幅で土塁・堀の輪郭を作り直した。'
            '土塁は天端が平らで、法面の勾配が一定である。虎口の通路は土塁を切り、土橋は堀を渡る形で表現した。'),
          Table([[img(A('scene_ev.png'), W * 0.495), img(A('scene_nat.png'), W * 0.495)]], colWidths=[W * 0.5] * 2),
          caption('図1 根拠色分け版(左: 橙=土塁、青=堀、灰青=河川側、ピンク=門・橋・建物)と自然色版(右)。')])]
    s += [P('4.3 VR体験の画面', h2),
          P('歩行(PCはW/A/S/D、VRは左スティック)、Tabキー(VRは右Aボタン)での表示切替、クリックでの解説表示を実装した。解説には内部の番号や記号を出さず、根拠を日本語の言葉だけで示す。'),
          Table([[img(A('game_gate.png'), W * 0.495), img(A('game_far.png'), W * 0.495)]], colWidths=[W * 0.5] * 2),
          caption('図2 現地スケールで歩いたときの画面(Game画面。左: 虎口の通路と石積み、右: 虎口と土塁を遠景から)。'),
          Spacer(1, 4), P('4.4 復元の根拠の内訳(32要素)', h2),
          P('台帳(32要素)の根拠区分は、位置・平面は「類例から推定(C)」と「仮説・復元演出(D)」だけで、<b>確認済み(A)の要素はまだ無い</b>。高さ・断面は、市の整備案の数値(B)が多い。'
            '現状は、提供された手彩色の図に依存した平面形であり、発掘図面で検証した段階ではない。この点を、第6節の課題の中心に置く。')]
    ch = Table([[barchart('位置・平面の根拠(32要素)', {'C': 18, 'D': 14}), barchart('高さ・断面の根拠(32要素)', {'B': 21, 'C': 2, 'D': 8, 'U': 1})]], colWidths=[W * 0.5] * 2)
    s += [ch, caption('図3 根拠の内訳。左右とも、確認済み(A)は0件。'), Spacer(1, 3),
          P('土塁の高さ・堀の深さは、市の「整備概要(案)」の寸法を使った。ただし、同案の「土量」は直方体の概算で実土量ではなく、数値の内部に不整合(虎口脇の石積みの高さと土塁高の比)もある。出典をたどって、報告書の実測値で置き換える。')]
    # ---- 5. 評価実験 ----
    s += [PageBreak(), P('5. 評価実験の計画', h1),
          table([['項目', '内容'],
                 ['デザイン', '被験者間比較。VR群 / 資料群(図面と解説パネル相当の資料)'],
                 ['人数・所要', '各群10〜15名(同学科の学生)。予備実験2〜3名。1人20〜30分(説明5分、体験10分、回答10分)'],
                 ['指標', '理解度テスト(体験前後の同一形式10問)、関心・没入感(5段階)、SUS(VR群)、VR酔い(簡易質問、VR群)、自由記述'],
                 ['分析', '事前・事後の得点差を群間比較(t検定またはMann-WhitneyのU検定)。自由記述は分類'],
                 ['問題文の作り方', '根拠表の「確認済み」の要素から作り、推定部分を正解にしない'],
                 ['VR酔い対策', '体験は10分以内、いつでも中断できる。移動は低速の歩行を基本とする']], [28 * mm, W - 28 * mm]),
          Spacer(1, 4), P('復元そのものの評価(利用者実験とは別)', h2),
          P('「歴史的に正しい」という単一の評価にせず、次の4指標に分けて評価する: 位置精度(基準点との誤差)、形状一致(設計図・発掘図の外郭線との平面差)、'
            '証拠トレーサビリティ(出典IDで参照できる部材の比率)、再現性(別の評価者が同じ資料から近い形を得られるか)。')]
    # ---- 6. 課題 ----
    s += [P('6. 課題と今後の予定', h1),
          table([['課題', '内容', '対応と時期'],
                 ['一次に近い史料の入手', '発掘報告書(第60集 本編・史料編)、設計図原本(歴彩館)、仕用帳が未入手。モデルは確認済み(A)の要素が無い', '市の文化財課・図書館(貸借・複写)・歴彩館へ11月上旬に依頼。到着は11月下旬の見込み'],
                 ['市資料の利用範囲', 'モデルと図は市の提供資料に基づく。論文・発表・VRでの利用範囲が未確認(Q14・Q17)', '文化財課へ11月上旬に確認。回答まで学内利用に限る'],
                 ['倫理審査', '被験者実験を含む。大学の「人を対象とする研究に関する倫理規定」が学生の実験・調査も対象とするため、要否を先生に確認', '指導教員に確認(11月上旬)。承認または非該当の判断後に実験を開始'],
                 ['モデルの精度', '西側・南側土塁の輪郭が粗い。川底標高は水際で代用。細部の部材が未実装', '資料入手後に実測値で更新。細部は後回し'],
                 ['VR実機', 'Quest 3での動作が未確認。日本語フォントの表示も要確認', '研究室のPCとQuest 3で、11月中旬までに確認']], [30 * mm, 74 * mm, W - 104 * mm]),
          Spacer(1, 5), P('今後の予定', h2),
          table([['期間', '内容'], ['〜11/14', 'Unity試作の完成(現況⇔復元の切替、実験用の画面、Quest実機の動作確認)、資料の発注'],
                 ['11/15〜11/21', '予備実験(2〜3名)、実験資料の確定(倫理審査の結果が前提)'], ['11/22〜12/5', '本実験'],
                 ['12/6〜12/25', '分析、論文、発表資料、アプリのビルド'], ['12/26〜12/31', 'レビュー反映、提出']], [28 * mm, W - 28 * mm])]
    s += [Spacer(1, 6), P('7. 報告で伺いたいこと', h1),
          B('倫理審査の要否と手続き(窓口、必要書類、審査にかかる期間)'),
          B('資料入手を、研究室や先生のルートで進められるか(歴彩館、市の文化財課)'),
          B('確認済み(A)の根拠が無い現段階で、実験(VR体験の効果の検証)を先に進めてよいか、それとも考証を優先すべきか')]
    doc.build(s)

if __name__ == '__main__':
    # 任意の第3引数: META を上書きする JSON(氏名・学籍番号など。gitには入れない)
    if len(sys.argv) > 3:
        import json
        META.update(json.load(open(sys.argv[3], encoding='utf-8')))
    build(sys.argv[1], sys.argv[2])
