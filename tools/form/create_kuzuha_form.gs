// 楠葉台場VR 体験アンケート(プロトタイプ)をGoogleフォームに自動作成する。
// 使い方: https://script.google.com で新しいプロジェクトを作り、このコードを貼り付け、createForm を実行(初回は権限の許可が必要)。
// 実行後、ログに編集用URLと回答用URLが出る。※倫理審査の判断を受けるまで、回答用URLを被験者に配らないこと。
// 注意: 回答の収集は匿名。メールアドレスは集めない設定にしている。
function createForm() {
  var form = FormApp.create('楠葉台場 VR体験アンケート(プロトタイプ)');
  form.setCollectEmail(false);
  form.setProgressBar(true);
  form.setShowLinkToRespondAgain(false);
  form.setAllowResponseEdits(false);
  form.setConfirmationMessage("ご協力ありがとうございました。回答は研究の目的以外には使いません。");
  form.setTitle("楠葉台場 VR体験アンケート");
  form.setDescription("このアンケートは、大阪工業大学の卒業研究「幕末期河川台場『楠葉台場』のVR復元と理解促進効果の検証」のためのものです。\n・所要時間: 約10分(VR体験は別に約10分)\n・参加は自由です。いつでも、理由を言わずに中断・取りやめができます。参加しなくても、不利益はありません(成績にも関係しません)。\n・氏名や学籍番号は聞きません。回答は番号(参加者ID)で匿名として扱い、研究の目的(卒業論文・発表)にのみ使い、個人が特定されない形で公表します。\n・VR体験で、気分が悪くなることがあります。その場合は、すぐに中断して休んでください。\n・連絡先: 【要記入: 研究者の氏名・メールアドレス / 指導教員: 平山 亮】");
  form.addCheckboxItem().setTitle("上記の内容を理解し、研究への参加に同意します。").setHelpText("同意いただける場合のみ、チェックして次へ進んでください。").setChoiceValues(["同意します"]).setRequired(true);
  form.addPageBreakItem().setTitle("あなたについて(匿名)").setHelpText("体験の前に、お答えください。");
  form.addTextItem().setTitle("参加者ID(実験者から伝えられた番号)").setRequired(true);
  form.addMultipleChoiceItem().setTitle("体験の条件(実験者が指示した記号)").setHelpText("実験者の指示に従ってください。").setChoiceValues(["A", "B"]).setRequired(true);
  form.addMultipleChoiceItem().setTitle("学年").setChoiceValues(["学部1年", "学部2年", "学部3年", "学部4年", "大学院", "その他"]).setRequired(true);
  form.addMultipleChoiceItem().setTitle("VR(ヘッドセット)の使用経験").setChoiceValues(["初めて", "数回ある", "月に数回以上使う"]).setRequired(true);
  form.addScaleItem().setTitle("体験の前、楠葉台場について、どの程度知っていましたか。").setBounds(1, 5).setLabels("全く知らなかった", "よく知っていた").setRequired(true);
  form.addScaleItem().setTitle("体験の前、歴史や史跡(城・台場など)にどの程度関心がありましたか。").setBounds(1, 5).setLabels("関心がない", "関心が高い").setRequired(true);
  form.addPageBreakItem().setTitle("体験の感想").setHelpText("VR体験を終えてから、お答えください。");
  form.addGridItem().setTitle("体験について、あてはまる程度を選んでください。").setRows(["VRの空間の中にいるように感じた", "体験に集中できた", "楠葉台場について、もっと知りたいと思った", "実際に現地を訪れてみたいと思った", "台場の全体の構造が理解できた", "歴史や史跡への関心が高まった"]).setColumns(["1 全くそう思わない", "2", "3", "4", "5 強くそう思う"]).setRequired(true);
  form.addScaleItem().setTitle("このアプリは、全体として使いやすかったですか。").setBounds(1, 5).setLabels("使いにくかった", "使いやすかった").setRequired(true);
  form.addGridItem().setTitle("体験中・体験後に、次のような症状はありましたか。").setRows(["気分が悪い(吐き気)", "頭痛", "目の疲れ", "めまい", "全体的な不快感"]).setColumns(["なし", "わずか", "中くらい", "強い"]).setRequired(true);
  form.addPageBreakItem().setTitle("復元の各部分の信頼度").setHelpText("ここからは、体験したモデルを思い出して答えてください(モデルは見られません)。\n次の各部分は、どの程度、資料にもとづいていると思いますか。");
  form.addGridItem().setTitle("各部分について、1〜5で選んでください。").setHelpText("1=想像に近い、5=確かな資料がある").setRows(["火薬庫の位置と形", "南面の虎口(出入口)の基礎", "番所の屋根・壁・間取り", "南面・西面が突き出した角(稜堡)の形をしていたこと", "北面の虎口に土橋があったこと", "大砲の種類・口径", "番所の位置と大きさ", "幕末当時の淀川の流れ"]).setColumns(["1 想像に近い", "2", "3", "4", "5 確かな資料がある"]).setRequired(true);
  form.addPageBreakItem().setTitle("文の真偽").setHelpText("同じく、モデルを思い出して答えてください。");
  form.addGridItem().setTitle("次の文は、正しいですか。").setRows(["番所の屋根の形は、史料で確定している。", "北面の虎口の土橋は、発掘調査で確認されている。", "火薬庫の場所と形は、発掘調査で確かめられている。", "京街道が台場の内側を迂回していた痕跡は、発掘調査で確認されている。"]).setColumns(["正しい", "誤り", "分からない"]).setRequired(true);
  form.addScaleItem().setTitle("ここまでの回答に、どの程度、自信がありますか。").setBounds(1, 5).setLabels("全く自信がない", "とても自信がある").setRequired(true);
  form.addPageBreakItem().setTitle("台場についての確認問題").setHelpText("最後の確認問題です。");
  form.addMultipleChoiceItem().setTitle("台場の南側にあった大きな堀は、何で造られていたことが、発掘で確認されていますか。").setChoiceValues(["石垣", "土だけ", "木の柵", "分からない"]).setRequired(true);
  form.addMultipleChoiceItem().setTitle("北側の土手は、南側と比べて、どのような規模でしたか。").setChoiceValues(["南側より小規模", "南側より大規模", "南側と同じ", "分からない"]).setRequired(true);
  form.addMultipleChoiceItem().setTitle("台場の西側の堀は、何にあたりますか。").setChoiceValues(["付け替えられた川", "用水路", "海につながる堀", "分からない"]).setRequired(true);
  form.addMultipleChoiceItem().setTitle("南の出入口から入って北の出入口へ抜けるとき、途中で通る建物はどれですか。").setChoiceValues(["番所", "火薬庫", "井戸の小屋", "分からない"]).setRequired(true);
  form.addPageBreakItem().setTitle("ご意見");
  form.addParagraphTextItem().setTitle("体験して、よかった点・分かりにくかった点・ご意見を教えてください。").setRequired(false);
  form.addScaleItem().setTitle("【根拠の色分けや解説があった方のみ】色の意味は、分かりやすかったですか。").setHelpText("根拠の提示がなかった方は、回答しなくて構いません。").setBounds(1, 5).setLabels("分かりにくかった", "分かりやすかった").setRequired(false);
  form.addScaleItem().setTitle("【根拠の色分けや解説があった方のみ】解説は、役に立ちましたか。").setBounds(1, 5).setLabels("役に立たなかった", "役に立った").setRequired(false);
  form.addMultipleChoiceItem().setTitle("【根拠の色分けや解説があった方のみ】解説を読んだ回数は、どのくらいですか。").setChoiceValues(["読んでいない", "1〜2回", "3〜5回", "6回以上"]).setRequired(false);
  Logger.log('編集用URL: ' + form.getEditUrl());
  Logger.log('回答用URL: ' + form.getPublishedUrl());
}
