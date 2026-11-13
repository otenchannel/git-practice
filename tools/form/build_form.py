# -*- coding: utf-8 -*-
"""評価アンケート(Googleフォーム)の仕様を1か所で持ち、次の3つを生成する。
  1. create_kuzuha_form.gs : Google Apps Script。Googleのスクリプトエディタに貼って実行すると、フォームが自動で作られる
  2. form-preview.pdf      : フォームの見た目の試作(プレビュー)。先生・同意前の確認用
  3. docs/form-prototype.md: 構成と正答表(実験者用)
使い方: python3 build_form.py <出力フォルダ>
注意: フォームの質問文には、内部の記号(A/B/C など)を出さない。正答表は実験者だけが持つ。"""
import json, os, sys

AGREE = ['1 全くそう思わない', '2', '3', '4', '5 強くそう思う']
CONF = ['1', '2', '3', '4', '5']
TRUST = ['1 想像に近い', '2', '3', '4', '5 確かな資料がある']
SSQ = ['なし', 'わずか', '中くらい', '強い']
JUDGE = ['確かめられている', '推定している', '分かっていない']
TF = ['正しい', '誤り', '分からない']

# 根拠表(data/evidence.csv)の要素から作った12項目。level は実験者用(フォームには出さない)
ELEM = [
    ('火薬庫の位置と形', 'U'), ('南面の虎口(出入口)の基礎', 'A'), ('番所の屋根・壁・間取り', 'C'), ('南面・西面が突き出した角(稜堡)の形をしていたこと', 'B'),
    ('北面の虎口に土橋があったこと', 'A'), ('大砲の種類・口径', 'U'), ('番所の位置と大きさ', 'B'), ('幕末当時の淀川の流れ', 'C')]
KEY_JUDGE = {'A': JUDGE[0], 'B': JUDGE[0], 'C': JUDGE[1], 'U': JUDGE[2]}
STATEMENTS = [
    ('番所の屋根の形は、史料で確定している。', '誤り'), ('北面の虎口の土橋は、発掘調査で確認されている。', '正しい'),
    ('火薬庫の場所と形は、発掘調査で確かめられている。', '誤り'), ('京街道が台場の内側を迂回していた痕跡は、発掘調査で確認されている。', '正しい')]
# 確認問題: (設問, 選択肢, 正解, 種別)。種別「解説」=クリックで出る解説に書かれている事実 / 「モデル」=歩いて見れば分かる事実(解説には書かない)
QUIZ = [
    ('台場の南側にあった大きな堀は、何で造られていたことが、発掘で確認されていますか。', ['石垣', '土だけ', '木の柵', '分からない'], '石垣', '解説'),
    ('北側の土手は、南側と比べて、どのような規模でしたか。', ['南側より小規模', '南側より大規模', '南側と同じ', '分からない'], '南側より小規模', '解説'),
    ('台場の西側の堀は、何にあたりますか。', ['付け替えられた川', '用水路', '海につながる堀', '分からない'], '付け替えられた川', '解説'),
    ('南の出入口から入って北の出入口へ抜けるとき、途中で通る建物はどれですか。', ['番所', '火薬庫', '井戸の小屋', '分からない'], '番所', 'モデル')]
SUS = ['このシステムを、頻繁に使いたいと思う', 'このシステムは、不必要に複雑だと感じた', 'このシステムは、使いやすいと思った',
       'このシステムを使うには、詳しい人のサポートが必要だと思う', 'このシステムの各機能は、うまくまとまっていると感じた',
       'このシステムには、一貫性のない部分が多いと感じた', 'ほとんどの人は、このシステムの使い方をすぐに覚えられると思う',
       'このシステムは、とても扱いにくいと感じた', 'このシステムを使うことに、自信があると感じた', 'このシステムを使い始める前に、多くのことを学ぶ必要があった']

INTRO = ('このアンケートは、大阪工業大学の卒業研究「幕末期河川台場『楠葉台場』のVR復元と理解促進効果の検証」のためのものです。\n'
         '・所要時間: 約10分(VR体験は別に約10分)\n・参加は自由です。いつでも、理由を言わずに中断・取りやめができます。参加しなくても、不利益はありません(成績にも関係しません)。\n'
         '・氏名や学籍番号は聞きません。回答は番号(参加者ID)で匿名として扱い、研究の目的(卒業論文・発表)にのみ使い、個人が特定されない形で公表します。\n'
         '・VR体験で、気分が悪くなることがあります。その場合は、すぐに中断して休んでください。\n・連絡先: 【要記入: 研究者の氏名・メールアドレス / 指導教員: 平山 亮】')

SECTIONS = [
    ('ご説明と同意', INTRO, [
        ('checkbox', '上記の内容を理解し、研究への参加に同意します。', ['同意します'], True, '同意いただける場合のみ、チェックして次へ進んでください。')]),
    ('あなたについて(匿名)', '体験の前に、お答えください。', [
        ('text', '参加者ID(実験者から伝えられた番号)', None, True, ''),
        ('choice', '体験の条件(実験者が指示した記号)', ['A', 'B'], True, '実験者の指示に従ってください。'),
        ('choice', '学年', ['学部1年', '学部2年', '学部3年', '学部4年', '大学院', 'その他'], True, ''),
        ('choice', 'VR(ヘッドセット)の使用経験', ['初めて', '数回ある', '月に数回以上使う'], True, ''),
        ('scale', '体験の前、楠葉台場について、どの程度知っていましたか。', ('全く知らなかった', 'よく知っていた'), True, ''),
        ('scale', '体験の前、歴史や史跡(城・台場など)にどの程度関心がありましたか。', ('関心がない', '関心が高い'), True, '')]),
    ('体験の感想', 'VR体験を終えてから、お答えください。', [
        ('grid', '体験について、あてはまる程度を選んでください。',
         (['VRの空間の中にいるように感じた', '体験に集中できた', '楠葉台場について、もっと知りたいと思った', '実際に現地を訪れてみたいと思った', '台場の全体の構造が理解できた', '歴史や史跡への関心が高まった'], AGREE), True, ''),
        ('scale', 'このアプリは、全体として使いやすかったですか。', ('使いにくかった', '使いやすかった'), True, ''),
        ('grid', '体験中・体験後に、次のような症状はありましたか。', (['気分が悪い(吐き気)', '頭痛', '目の疲れ', 'めまい', '全体的な不快感'], SSQ), True, '')]),
    ('復元の各部分の信頼度', 'ここからは、体験したモデルを思い出して答えてください(モデルは見られません)。\n次の各部分は、どの程度、資料にもとづいていると思いますか。',
     [('grid', '各部分について、1〜5で選んでください。', ([e for e, _ in ELEM], TRUST), True, '1=想像に近い、5=確かな資料がある')]),
    ('文の真偽', '同じく、モデルを思い出して答えてください。',
     [('grid', '次の文は、正しいですか。', ([t for t, _ in STATEMENTS], TF), True, ''),
      ('scale', 'ここまでの回答に、どの程度、自信がありますか。', ('全く自信がない', 'とても自信がある'), True, '')]),
    ('台場についての確認問題', '最後の確認問題です。',
     [('choice', q, opts, True, '') for q, opts, _, _ in QUIZ]),
    ('ご意見', '', [
        ('paragraph', '体験して、よかった点・分かりにくかった点・ご意見を教えてください。', None, False, ''),
        ('scale', '【根拠の色分けや解説があった方のみ】色の意味は、分かりやすかったですか。', ('分かりにくかった', '分かりやすかった'), False, '根拠の提示がなかった方は、回答しなくて構いません。'),
        ('scale', '【根拠の色分けや解説があった方のみ】解説は、役に立ちましたか。', ('役に立たなかった', '役に立った'), False, ''),
        ('choice', '【根拠の色分けや解説があった方のみ】解説を読んだ回数は、どのくらいですか。', ['読んでいない', '1〜2回', '3〜5回', '6回以上'], False, '')]),
]
CONFIRM = 'ご協力ありがとうございました。回答は研究の目的以外には使いません。'

def js(x): return json.dumps(x, ensure_ascii=False)

def gen_gs():
    L = ['// 楠葉台場VR 体験アンケート(プロトタイプ)をGoogleフォームに自動作成する。',
         '// 使い方: https://script.google.com で新しいプロジェクトを作り、このコードを貼り付け、createForm を実行(初回は権限の許可が必要)。',
         '// 実行後、ログに編集用URLと回答用URLが出る。※倫理審査の判断を受けるまで、回答用URLを被験者に配らないこと。',
         '// 注意: 回答の収集は匿名。メールアドレスは集めない設定にしている。',
         'function createForm() {',
         "  var form = FormApp.create('楠葉台場 VR体験アンケート(プロトタイプ)');",
         '  form.setCollectEmail(false);', '  form.setProgressBar(true);', '  form.setShowLinkToRespondAgain(false);',
         '  form.setAllowResponseEdits(false);', '  form.setConfirmationMessage(' + js(CONFIRM) + ');']
    for si, (title, desc, items) in enumerate(SECTIONS):
        if si > 0:
            L.append('  form.addPageBreakItem().setTitle(%s)%s;' % (js(title), '.setHelpText(%s)' % js(desc) if desc else ''))
        else:
            L.append('  form.setTitle(%s);' % js('楠葉台場 VR体験アンケート'))
            L.append('  form.setDescription(%s);' % js(desc))
        for kind, q, opt, req, help_ in items:
            h = '.setHelpText(%s)' % js(help_) if help_ else ''
            r = '.setRequired(%s)' % ('true' if req else 'false')
            if kind == 'checkbox': L.append('  form.addCheckboxItem().setTitle(%s)%s.setChoiceValues(%s)%s;' % (js(q), h, js(opt), r))
            elif kind == 'text': L.append('  form.addTextItem().setTitle(%s)%s%s;' % (js(q), h, r))
            elif kind == 'paragraph': L.append('  form.addParagraphTextItem().setTitle(%s)%s%s;' % (js(q), h, r))
            elif kind == 'choice': L.append('  form.addMultipleChoiceItem().setTitle(%s)%s.setChoiceValues(%s)%s;' % (js(q), h, js(opt), r))
            elif kind == 'scale': L.append('  form.addScaleItem().setTitle(%s)%s.setBounds(1, 5).setLabels(%s, %s)%s;' % (js(q), h, js(opt[0]), js(opt[1]), r))
            elif kind == 'grid': L.append('  form.addGridItem().setTitle(%s)%s.setRows(%s).setColumns(%s)%s;' % (js(q), h, js(opt[0]), js(opt[1]), r))
    L += ["  Logger.log('編集用URL: ' + form.getEditUrl());", "  Logger.log('回答用URL: ' + form.getPublishedUrl());", '}']
    return '\n'.join(L) + '\n'

def gen_md():
    M = ['# 評価アンケート(Googleフォーム)の試作', '',
         '状態: 試作(2026-11-13)。**倫理審査の要否が確認できるまで、被験者に配布しない。** 作り方は `tools/form/create_kuzuha_form.gs`(Google Apps Script)。', '',
         '## 構成', '| ページ | 内容 | 設問数 |', '|---|---|---|']
    for t, _, it in SECTIONS: M.append('| %s | %s | %d |' % (t, '、'.join(sorted(set(k for k, *_ in it))), len(it)))
    rank = {'A': 4, 'B': 3, 'C': 2, 'U': 1}
    lab = {'A': '確認済み', 'B': '史料に記載', 'C': '類例から推定', 'U': '資料不足'}
    M += ['', '## 実験者用の正答表(フォームには出さない)', '### ページ4: 復元の8つの部分(信頼度)', '| 項目 | 根拠の強さ(点数) |', '|---|---|']
    for e, lv in ELEM: M.append('| %s | %s(%d) |' % (e, lab[lv], rank[lv]))
    M += ['', '- 主要評価(根拠の較正) = 根拠の強い部分(確認済み・史料に記載)の信頼度の平均 − 弱い部分(類例から推定・資料不足)の信頼度の平均。大きいほど、信頼を根拠の強さに応じて変えられている',
          '- 参考: 各人の信頼度と根拠の強さ(A=4, B=3, C=2, U=1)の順位相関(Spearman)も、8項目から算出できる(不安定なので補助)',
          '', '### ページ5: 文の真偽(誤認率)', '| 文 | 正解 |', '|---|---|']
    for t, a in STATEMENTS: M.append('| %s | %s |' % (t, a))
    M += ['', '- 誤認率 = 「推定の部分を事実と言い切る文」(誤りの文)を「正しい」と答えた割合。正しい文を「誤り」と答える過剰な疑いも別に集計',
          '', '### ページ6: 確認問題(種別つき)', '| 設問 | 正解 | 種別 |', '|---|---|---|']
    for q, _, a, k in QUIZ: M.append('| %s | %s | %s |' % (q, a, k))
    M += ['', '- 種別「解説」: クリックで出る解説に書かれた事実。提示ありの群が、解説を読んで学べたかを見る',
          '- 種別「モデル」: 歩けば分かる事実(解説には書かない)。解説の効果と、空間の把握の効果を区別するための対照',
          '- 解説の内容は `unity/KuzuhaDaiba/Assets/Scripts/ObjectDescriptions.cs`。**解説の文面を変えたら、種別「解説」の問題を必ず見直す**',
          '- 解説を実際に読んだか(どの物をクリックしたか)は、アプリのログと参加者IDで確認する。読んでいない問題は、解析から分けて扱う',
          '', '## 注意',
          '- 8項目の根拠の強さは、`data/evidence.csv` の判断(私たちの解釈)による。問題を確定する前に、指導教員か第三者の確認を受ける',
          '- 問題の出し方: ページ4の質問文に、ページ6の正解(石垣など)を出さない。順序の影響に注意',
          '- ページ6の正解は、公的解説の要約と、解説の文面にもとづく。原資料での確認は未了',
          '- 使いやすさは1問(時短案A)。SUS(10問)の標準得点は出せない。必要になったら、SUSの定訳を確認して戻す',
          '- 体験時間とクリック数は、アプリ側の記録と、参加者IDで結びつける(フォームには含めない)',
          '- 氏名・学籍番号・メールアドレスは集めない。「条件」は、実験者が指示する(ランダムに近い割り当て)']
    return '\n'.join(M) + '\n'

def gen_pdf(path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    pdfmetrics.registerFont(TTFont('JP', '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf'))
    F = lambda n, **k: ParagraphStyle(n, fontName='JP', fontSize=k.pop('fs', 9.5), leading=k.pop('ld', 14), wordWrap='CJK', textColor=k.pop('textColor', colors.HexColor('#1f2933')), **k)
    st, h1, h2, sm = F('b'), F('h1', fs=15, ld=21, textColor=colors.HexColor('#5b2a86')), F('h2', fs=11, ld=16), F('s', fs=8, ld=12, textColor=colors.HexColor('#5b6770'))
    W = A4[0] - 36 * mm
    P = lambda t, s=st: Paragraph(t.replace('\n', '<br/>'), s)
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm, title='評価アンケート(Googleフォーム)試作プレビュー')
    s = [P('楠葉台場 VR体験アンケート', h1), P('Googleフォーム 試作のプレビュー(実際の見た目とは多少異なります)。回答は匿名、メールアドレスは集めません。', sm),
         P('※ 倫理審査の要否が確認できるまで、被験者には配布しません。', sm), Spacer(1, 6)]
    for si, (title, desc, items) in enumerate(SECTIONS):
        blk = [P('ページ%d: %s' % (si + 1, title), h2)]
        if desc: blk.append(P(desc, st))
        first = True
        for kind, q, opt, req, help_ in items:
            tag = {'checkbox': 'チェックボックス', 'text': '記述(短文)', 'paragraph': '記述(長文)', 'choice': '単一選択', 'scale': '5段階', 'grid': '表(行×列)'}[kind]
            det = []
            if help_: det.append(help_)
            if kind in ('checkbox', 'choice'): det.append('　'.join('○ ' + o for o in opt))
            if kind == 'scale': det.append('1 ' + opt[0] + '  ……  5 ' + opt[1])
            if kind == 'grid':
                rws, cols = opt
                det.append('列: ' + ' / '.join(cols)); det.append('行(%d): ' % len(rws) + ' ／ '.join(rws))
            rows = [[P('<b>%s</b>%s' % (q, ' <font color="#c0392b">*</font>' if req else ''), st), P(tag, sm)]]
            sty = [('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cfd6dc')), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]
            if det:
                rows.append([P('<br/>'.join(det), sm), '']); sty.append(('SPAN', (0, 1), (1, 1)))
            t = Table(rows, colWidths=[W - 28 * mm, 28 * mm]); t.setStyle(TableStyle(sty))
            if first:
                blk.append(Spacer(1, 2)); blk.append(t); first = False
                s.append(KeepTogether(blk)); s.append(Spacer(1, 3))
            else:
                s += [KeepTogether([t]), Spacer(1, 3)]
        s.append(Spacer(1, 6))
    s += [P('完了メッセージ: ' + CONFIRM, sm)]
    doc.build(s)

if __name__ == '__main__':
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'create_kuzuha_form.gs'), 'w', encoding='utf-8').write(gen_gs())
    open(os.path.join(out, 'form-prototype.md'), 'w', encoding='utf-8').write(gen_md())
    gen_pdf(os.path.join(out, 'form-preview.pdf'))
    print('ok', out)
