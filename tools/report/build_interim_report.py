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
    s += [Spacer(1, 34 * mm), P(META['sub'], S('t0', fontSize=12, textColor=ACC)), Spacer(1, 4),
          P(META['title'], S('t1', fontSize=21, leading=31)), Spacer(1, 10),
          P('時代考証にもとづく根拠つきの3D復元と、その根拠の提示が利用者の理解に与える効果の検証', S('t2', fontSize=11, textColor=MUTED)), Spacer(1, 18 * mm)]
    s += [table([['発表日', META['date']], ['氏名', f'{META["name"]}(学籍番号 {META["sid"]})'], ['指導', META['adv']]], [28 * mm, W - 28 * mm], head=False, zebra=False),
          Spacer(1, 12 * mm), img(A('game_far.png'), W * 0.78), Spacer(1, 3), caption('図0 試作したVRアプリの画面(南側の虎口と土塁を遠景から)。')]
    s += [PageBreak()]
    # ---- 1. 要旨 ----
    s += [P('1. 要旨', h1),
          P('楠葉台場跡(大阪府枚方市、国史跡)は、慶応元年(1865)に完成した、淀川左岸の河川台場である。現地は史跡公園として整備されているが、堀や土塁の配置、番所や虎口などの構造は、現地を歩くだけでは把握しにくい。'
            '本研究は、時代考証にもとづく3D復元をUnity(Meta Quest 3)で構築し、その復元を利用者が体験するVRアプリを作る。'),
          P('これまでに、市の提供資料と国土地理院の標高から位置合わせした3Dモデルと、歩行・表示切替・クリック解説を備えたVRアプリの試作を、PC上で動かせる段階に達した。'
            'ただし、先生から「形は悪くないが、考証の手法に新しさや優れた点がなければ研究とは言えない」とのご指摘を受けており、<b>研究の主張(新規性)の再設定が、現在の最大の課題</b>である。本報告では、現状の整理と、再設定の案を示す。'),
          Spacer(1, 3), P('今回の報告の要点', h2),
          B('<b>成果:</b> 縮尺・方位・標高を割り出して位置合わせした、32要素の3Dモデルと、VRアプリの試作(第4節)'),
          B('<b>現状認識:</b> 現在の成果は「復元の制作」に近く、手法としての新規性は未確立。確認済みの根拠(発掘図面での検証)も無い(第2節・第4節)'),
          B('<b>再設定案:</b> 限られた資料から、誤差の見積りと根拠(出典・導出過程)を伴って復元する手法と、その不確かさを利用者に示す効果を、研究の主張とする。実行しやすさから、利用者実験(④)を軸にする方針(第2節)'),
          B('<b>課題:</b> 先行研究の調査、報告書・設計図原本の入手、市資料の利用範囲の確認、倫理審査の確認(第6節)')]
    # ---- 2. 研究の位置づけ ----
    s += [P('2. 研究の位置づけと新規性(先生のご指摘を受けた再設定案)', h1),
          P('2.1 ご指摘と現状認識', h2),
          P('ご指摘の要旨は、「形(復元物)は悪くないが、時代考証を行うなら、その手法が新しい、または優れていなければ研究とは言えない」というものである。'
            '現状の研究計画は、「復元を作り、VR体験の効果を測る」という構成であり、考証の手法そのものに主張がない。デジタル復元で根拠と推定を区別して示すことは、既存の指針(ロンドン憲章、セビリア原則など)でも求められており、それだけでは新規性にならない。'),
          P('2.2 研究の主張の再設定案', h2),
          P('資料が少ない対象で、<b>「どこまでが根拠で、どこからが推定か」を、誤差の大きさと導出過程つきで示す復元の手法</b>を提案し、<b>その提示が、利用者による推定と事実の取り違えを減らすか</b>を検証する。'),
          table([['候補', '内容', '本研究での手がかり(現状)', '必要な作業'],
                 ['① 誤差の見積り', '縮尺のない手彩色図と地理院データから位置合わせし、誤差を部材ごとに見積もる', '縮尺0.353 m/px(±3%)、東辺で0.4 m以内の一致を確認済み。誤差の見積りは第4.3節', '実測・報告書図面で検証'],
                 ['② 資料間の整合の検証', '複数の資料(手彩色図、整備案、標高)の寸法の食い違いを検出し、復元への影響を調べる', '北・東の土手の延長(約260 m対350 m)、石積みと土塁の高さの比に不整合を発見', '感度分析(寸法を動かしたときの形の変化)'],
                 ['③ 導出過程の記録', '各部材に、出典・変換・誤差・採用理由を持たせ、利用者が見られるようにする', '根拠の5段階と出典台帳(29件)、解説UIを試作', '導出過程の様式化と、一覧での提示'],
                 ['④ 利用者への効果', '根拠・誤差を示すと、推定部分を事実と誤解しなくなるか(理解の較正)', '評価実験の枠組み(第5節)', '倫理審査、問題文の再設計']], [22 * mm, 50 * mm, 56 * mm, W - 128 * mm]),
          Spacer(1, 3),
          P('<b>注意:</b> 上の4候補が先行研究に対して新しいかどうかは、まだ確認していない。<b>先行研究の調査(デジタル遺産の復元における不確実性の可視化、根拠の記録様式、根拠提示の利用者評価)を最優先で行い、新しいと言える範囲を絞る</b>。'
            '絞った結果、①〜④のうち一部に集中する可能性がある。', small),
          Spacer(1, 3), P('<b>現時点の方針(学生側の案):</b> 利用者実験を軸にする(④)。ゼミ内外の学生から回答を集められる見込みがあり、実行しやすいため。比較する条件は、すでにUnity内で切り替えられる「自然色(根拠の提示なし)」「根拠の色分け」「色分け+クリックでの解説(根拠を言葉で提示)」を想定する。②(資料間の整合・感度分析)は、条件を作る材料として補助的に扱う。実験は倫理審査の判断を受けてから行う。', body),
          Spacer(1, 3), KeepTogether([P('2.3 リサーチクエスチョン(再設定案)', h2),
          table([['RQ1', '限られた資料から、誤差と根拠を伴って復元する手法は、再現可能で、検証できるか(位置の誤差、資料間の整合、別の評価者による再現性)'],
                 ['RQ2', '根拠・誤差の提示は、利用者が「確かな部分」と「推定の部分」を見分ける力を高めるか(あわせて、空間理解と関心)']], [14 * mm, W - 14 * mm], head=False)]),
          Spacer(1, 4), P('2.4 先行研究の一次整理(11/11時点。英語文献の検索結果にもとづき、多くは要旨のみ確認。全文は未読、日本語文献は未調査)', h2),
          table([['分野', '代表的な研究', '本研究との関係'],
                 ['根拠・不確実性の記録と可視化', 'Apollonioら(2015〜2024)、Cazzaro(2023)、Demetrescu(2015・2023、Extended Matrix)', '根拠の記録・色での表示は既に提案済み。③と「VRで色分け」だけでは新規性にならない'],
                 ['信頼性の定量化', 'Hermonら(2006)、Foschiら(2024)', '信頼性指標・平均の不確実性の算出法が提案済み'],
                 ['指針', 'ロンドン憲章(2006〜)、セビリア原則(2011)', '透明性・文書化を要請。実装は不十分との指摘もある'],
                 ['利用者評価', 'Houdeら、Sifniotisら(2007)、Mekheimar(2024、VR)、ISPRS(2026、VRで根拠レベルを色分け)', '表現方式の比較は3Dで少数。VRでの比較は空白の可能性。2026年の論文が最も近く、全文は未読'],
                 ['日本の近世遺跡', '小諸城のCG復元など', '不確実性の表示と利用者評価を扱う研究は、今回の検索では見つからず']], [34 * mm, 62 * mm, W - 96 * mm]),
          Spacer(1, 2), P('<b>暫定の見立て:</b> ②(資料間の整合の検証・感度分析)と④(VRでの表現方式の比較と、日本の近世遺跡への適用)に空白の可能性がある。ただし網羅的な調査ではなく、確認が必要。', small)]
    # ---- 3. 方法 ----
    s += [Spacer(1, 6), P('3. 時代考証の方法と進捗', h1),
          P('史料を強さの順に4層(発掘・実測 / 同時代の史料 / 現代の整理 / 類例・現在の地形)に分け、要素ごとに、根拠の強さを5段階で記録している。出典は台帳(29件)と、未解決の問い(24件)で管理する。')]
    lv = Table([[Paragraph(f'<b>{k}</b> {LVN[k]}', S('lv', fontSize=8.5, leading=12, textColor=colors.white, alignment=1)) for k in 'ABCDU']], colWidths=[W / 5] * 5)
    lv.setStyle(TableStyle([('BACKGROUND', (i, 0), (i, 0), colors.HexColor(LV[k])) for i, k in enumerate('ABCDU')] + [('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    s += [Spacer(1, 3), lv, Spacer(1, 4),
          table([['段階', '内容', '期間', '状態'],
                 ['0', '研究設計(題目・RQ・実験案)', '〜10/8', '完了(RQは再設定案を第2節に提示)'],
                 ['1', '資料収集・台帳', '10/8〜', '8割(報告書本編・設計図原本は未入手)'],
                 ['2', '開発環境(Unity 6.6 / URP / XR)', '〜10/14', '完了'],
                 ['3', '地形・遺構の3D化', '10/14〜10/31', 'ほぼ完了(細部の改善は継続)'],
                 ['4', 'Unity試作(歩行・表示切替・クリック解説)', '10/20〜11/14', '進行中(PCで動作確認済み)'],
                 ['5', '予備実験・実験資料の確定', '11/15〜11/21', '未着手(研究の主張の再設定が先)'],
                 ['6', '本実験', '11/22〜12/5', '未着手'],
                 ['7', '分析・考察', '12/6〜12/14', '未着手'],
                 ['8', '論文執筆・発表資料・ビルド', '12/15〜12/25', '未着手'],
                 ['9', 'レビュー反映・提出', '12/26〜12/31', '未着手']], [12 * mm, 70 * mm, 28 * mm, W - 110 * mm])]
    # ---- 4. 成果 ----
    s += [Spacer(1, 4), P('4. 成果', h1), P('4.1 3Dモデルの構築(位置合わせ)', h2),
          P('提供された地形図は、縮尺の記載が無いA4の写真で、上が北である。現在も変わらない地物(台場の東辺と京阪線路の距離、南の道路の長さ)を、国土地理院の地図で測り、<b>縮尺を 0.353 m/px(約1/2,300、誤差±3%)</b>と決定した。'
            'Y=0(基準の高さ)は、国土地理院の標高データ(約5mメッシュ)から求めた淀川の水際の標高 <b>5.0 m (T.P.)</b> とした。川底は水面下で測られていないため、水際で代用している。'
            '手彩色の区画は、東端の辺を基準にした向きに揃え、整備案の幅・高さで、直線と一定幅の輪郭に作り直した。土塁は天端が平らで、法面の勾配が一定である。')]
    flow = Drawing(W, 17 * mm); xs = [0, 0.26, 0.52, 0.78]; labs = ['写真 → m', '地図・標高に位置合わせ', '輪郭を直線化', '立体化・色付け']
    for x, lab in zip(xs, labs):
        flow.add(Rect(x * W, 3 * mm, 0.21 * W, 11 * mm, fillColor=colors.HexColor('#eaf2f7'), strokeColor=ACC, strokeWidth=0.6))
        flow.add(String(x * W + 0.105 * W, 7.2 * mm, lab, fontName='JP', fontSize=8, fillColor=INK, textAnchor='middle'))
    for x in xs[:-1]:
        flow.add(Line((x + 0.21) * W, 8.5 * mm, (x + 0.26) * W, 8.5 * mm, strokeColor=ACC, strokeWidth=1))
    s += [flow, Spacer(1, 3), P('4.2 VRアプリの試作', h2),
          P('歩行(PCはW/A/S/D、VRは左スティック)、Tabキー(VRは右Aボタン)での根拠色分け版と自然色版の切替、クリック(VRは右トリガー)での解説表示を実装した。解説は、内部の記号や番号を使わず、根拠を日本語の言葉で示す。'),
          Table([[img(A('top_nat.png'), W * 0.4), img(A('top_ev.png'), W * 0.4)]], colWidths=[W * 0.5] * 2),
          caption('図1 真上から見た全体。左: 自然色版、右: 根拠色分け版(橙=土塁、青=堀、灰青=河川側、ピンク=門・橋・建物)。Unity内でTabキーにより切り替えられる。'),
          Spacer(1, 3),
          Table([[img(A('game_gate.png'), W * 0.495), img(A('game_gate2.png'), W * 0.495)]], colWidths=[W * 0.5] * 2),
          caption('図2 現地スケールで歩いたときの画面(左: 虎口の通路と両側の石積み、右: 虎口の門と石積み)。')]
    # 4.3 誤差
    s += [PageBreak(), P('4.3 位置の誤差の見積り(暫定。概算であり、実測では未検証)', h2),
          P('再設定案の①に当たる。現状の位置合わせで見込まれる誤差を、要因ごとに整理した。台場の広がりは約300 mで、番所(原点)から端までは最大およそ150 mである。'),
          table([['要因', '大きさ', '原点から150 mでの影響', '根拠・前提'],
                 ['縮尺', '±3%', '約±4.5 m', '東辺と線路の距離、道路の長さの2測定の差'],
                 ['方位', '補正0.58°、不確かさは同程度と仮定', '約±1.6 m', '南の道路と地理院地図の方位差。不確かさは仮定'],
                 ['写真の台形歪み', '水平方向で最大約7%(未補正)', '最大約10 m(上限の目安)', '紙面の歪みを補正していない'],
                 ['原点(番所)の位置', '数m〜十数m', '全体に一様にずれる', '番所を現在の地図に合わせた値'],
                 ['東辺(基準線)', '0.4 m以内で一致', '東辺付近では小さい', '東の堀の外縁と地理院の境界線との比較']], [30 * mm, 42 * mm, 42 * mm, W - 114 * mm]),
          Spacer(1, 3),
          P('<b>読み取れること:</b> 平面位置の誤差は、基準にした東辺の付近では小さいが、西側へ行くほど大きくなり、堀の幅(6〜12 m)と同程度になりうる。'
            '一方、高さ・深さは、市の「整備概要(案)」の寸法をそのまま使っており、実測値ではない。標高の地面は、約5 mメッシュの標高データを平滑化したもので、細かな起伏は表現されない。'
            '<b>この誤差の大きさを、利用者に見える形で示すこと</b>が、再設定案の③④につながる。')]
    s += [Spacer(1, 3), P('4.4 復元の根拠の内訳(32要素)', h2),
          P('位置・平面は「類例から推定(C)」と「仮説・復元演出(D)」だけで、<b>確認済み(A)の要素はまだ無い</b>。高さ・断面は、市の整備案の数値(B)が多い。提供された手彩色の図に依存した平面形であり、発掘図面で検証した段階ではない。')]
    ch = Table([[barchart('位置・平面の根拠(32要素)', {'C': 18, 'D': 14}), barchart('高さ・断面の根拠(32要素)', {'B': 21, 'C': 2, 'D': 8, 'U': 1})]], colWidths=[W * 0.5] * 2)
    s += [ch, caption('図3 根拠の内訳。左右とも、確認済み(A)は0件。'), Spacer(1, 3),
          P('同案の「土量」は直方体の概算で実土量ではなく、数値の内部に不整合(北・東の土手の延長が約260 m対350 m、虎口脇の石積みと土塁の高さの比)もある。これらは再設定案②の手がかりとして扱う。')]
    # ---- 5. 評価実験 ----
    s += [PageBreak(), P('5. 評価実験の計画(再設定案に合わせて見直し中)', h1),
          table([['項目', '内容'],
                 ['デザイン', '被験者間比較。「根拠・誤差を提示するVR」群 / 「提示しないVR」群(必要に応じて資料閲覧群)'],
                 ['人数・所要', '各群10〜15名(同学科の学生)。予備実験2〜3名。1人20〜30分(説明5分、体験10分、回答10分)'],
                 ['指標', '推定部分を事実と取り違える割合(「確かな部分」「推定の部分」の判別テスト)、理解度テスト(体験前後)、関心・没入感(5段階)、SUS、VR酔い(簡易質問)、自由記述'],
                 ['分析', '群間比較(t検定またはMann-WhitneyのU検定)。自由記述は分類'],
                 ['問題文の作り方', '根拠表の「確認済み」「史料に記載」の要素から作り、推定部分を正解にしない'],
                 ['VR酔い対策', '体験は10分以内、いつでも中断できる。移動は低速の歩行を基本とする']], [28 * mm, W - 28 * mm]),
          Spacer(1, 4), P('復元そのものの評価(RQ1)', h2),
          P('「歴史的に正しい」という単一の評価にせず、4指標に分けて評価する: 位置精度(基準点との誤差)、形状一致(設計図・発掘図の外郭線との平面差)、証拠トレーサビリティ(出典IDで参照できる部材の比率)、再現性(別の評価者が同じ資料から近い形を得られるか)。')]
    # ---- 6. 課題 ----
    s += [P('6. 課題と今後の予定', h1),
          table([['課題', '内容', '対応と時期'],
                 ['研究の主張(新規性)', '考証の手法の新しさ・優れた点が未確立(先生のご指摘)。一次整理では、③は既存。②④に空白の可能性', '主要論文の全文読解と日本語文献の調査(〜11/20)。②④を軸に、範囲を決める'],
                 ['一次に近い史料の入手', '発掘報告書(第60集)、設計図原本(歴彩館)、仕用帳が未入手。確認済み(A)の要素が無い', '市の文化財課・図書館・歴彩館へ依頼(発注の状況は報告時に補足)'],
                 ['市資料の利用範囲', '論文・発表・VRでの利用範囲が未確認', '文化財課へ確認。回答まで学内利用に限る'],
                 ['倫理審査', '被験者実験を含む。大学の「人を対象とする研究に関する倫理規定」が学生の実験・調査も対象とするため、要否を確認', '先生に要否を確認。承認または非該当の判断後に実験を開始'],
                 ['VR実機', 'Quest 3での動作と、日本語フォントの表示が未確認', '研究室のPCとQuest 3で確認(11月中旬)']], [30 * mm, 74 * mm, W - 104 * mm]),
          Spacer(1, 5), P('今後の予定', h2),
          table([['期間', '内容'], ['〜11/20', '先行研究の調査、研究の主張・RQの確定、資料の発注、Unity試作の完成'],
                 ['11/21〜11/28', '誤差見積りの精緻化(実測・図面での検証)、実験資料の確定、倫理審査の手続き'],
                 ['11/29〜12/12', '(承認後)予備実験・本実験。実験の規模は主張の絞り込みに合わせて縮小もありうる'], ['12/13〜12/25', '分析、論文、発表資料、アプリのビルド'], ['12/26〜12/31', 'レビュー反映、提出']], [28 * mm, W - 28 * mm])]
    s += [Spacer(1, 6), P('7. 報告で伺いたいこと', h1),
          B('研究の主張として、④(利用者実験)を軸にし、②を補助とする方針でよいか。「適用・比較・検証」による新しさで足りるか。先行研究の調査で、特に見るべき分野・文献はあるか'),
          B('倫理審査の要否と手続き(窓口、必要書類、審査にかかる期間)'),
          B('資料入手を、研究室や先生のルートで進められるか(歴彩館、市の文化財課)'),
          B('確認済み(A)の根拠が無い現段階で、実験を先に進めるべきか。それとも、考証の検証を優先すべきか')]
    doc.build(s)

if __name__ == '__main__':
    # 任意の第3引数: META を上書きする JSON(氏名・学籍番号など。gitには入れない)
    if len(sys.argv) > 3:
        import json
        META.update(json.load(open(sys.argv[3], encoding='utf-8')))
    build(sys.argv[1], sys.argv[2])
