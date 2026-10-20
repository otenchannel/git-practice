using System.Text;
using UnityEngine;
using UnityEngine.UI;

// 視線(頭の正面)で見ている物の解説を、視界に固定したパネルに表示する。
//  - 建物・門・土橋・井戸など: オブジェクト名から台帳(object-ledger.csv)を引く
//  - 土塁・堀: 地形メッシュ上の当たり位置から features.json の足元ポリゴンで判定する
// 根拠レベルは色+文字(A/B/C/D/U)で併記する。
public class InfoPanel : MonoBehaviour
{
    public Transform head;
    public ModelSwitcher switcher;     // 現在どちらのモデルかを表示するため(任意)
    public float maxDistance = 120f;
    public float panelDistance = 1.6f;
    public Vector2 panelSize = new Vector2(0.9f, 0.55f);

    Text text; Image bar; Transform panel; string lastId;

    void Start()
    {
        if (head == null && Camera.main != null) head = Camera.main.transform;
        Build();
    }

    void Build()
    {
        var go = new GameObject("InfoPanel"); panel = go.transform; panel.SetParent(head, false);
        panel.localPosition = new Vector3(0f, -0.28f, panelDistance); panel.localScale = Vector3.one * 0.001f;
        var cv = go.AddComponent<Canvas>(); cv.renderMode = RenderMode.WorldSpace;
        panel = go.transform;  // Canvas追加で Transform が RectTransform に置き換わるため取り直す
        var rt = go.GetComponent<RectTransform>(); rt.sizeDelta = panelSize * 1000f;
        var bg = new GameObject("bg").AddComponent<Image>(); bg.transform.SetParent(panel, false); bg.color = new Color(0, 0, 0, 0.65f);
        var brt = bg.rectTransform; brt.anchorMin = Vector2.zero; brt.anchorMax = Vector2.one; brt.offsetMin = brt.offsetMax = Vector2.zero;
        bar = new GameObject("bar").AddComponent<Image>(); bar.transform.SetParent(panel, false);
        var rr = bar.rectTransform; rr.anchorMin = new Vector2(0, 0); rr.anchorMax = new Vector2(0, 1); rr.pivot = new Vector2(0, 0.5f); rr.sizeDelta = new Vector2(14, 0); rr.anchoredPosition = Vector2.zero;
        var t = new GameObject("text"); t.transform.SetParent(panel, false);
        text = t.AddComponent<Text>(); text.font = JapaneseFont(); text.fontSize = 34; text.color = Color.white; text.horizontalOverflow = HorizontalWrapMode.Wrap; text.verticalOverflow = VerticalWrapMode.Truncate;
        var trt = text.rectTransform; trt.anchorMin = Vector2.zero; trt.anchorMax = Vector2.one; trt.offsetMin = new Vector2(32, 12); trt.offsetMax = new Vector2(-16, -12);
        panel.gameObject.SetActive(false);
    }

    static Font JapaneseFont()
    {
        // PC: Yu Gothic / Meiryo。Quest(Android): Noto Sans CJK 系。見つからなければ既定フォント(日本語が出ない場合は TMP の日本語フォントに差し替える)
        var f = Font.CreateDynamicFontFromOSFont(new[] { "Yu Gothic UI", "Meiryo", "Noto Sans CJK JP", "Noto Sans JP", "Droid Sans Fallback", "Arial" }, 34);
        return f != null ? f : Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
    }

    void Update()
    {
        if (head == null || ObjectLedger.Instance == null) return;
        ObjectLedger.Row row = null; Vector3 hitPoint = default;
        if (Physics.Raycast(head.position, head.forward, out var hit, maxDistance, ~0, QueryTriggerInteraction.Ignore))
        {
            hitPoint = hit.point;
            row = ObjectLedger.Instance.FindByObjectName(hit.collider.name);
            if (row == null) row = ObjectLedger.Instance.FindByPosition(hit.point);
        }
        if (row == null) { if (panel.gameObject.activeSelf) panel.gameObject.SetActive(false); lastId = null; return; }
        if (row.Id != lastId) { lastId = row.Id; Show(row); }
        if (!panel.gameObject.activeSelf) panel.gameObject.SetActive(true);
    }

    static EvidenceLevel Parse(string s) => (s ?? "").Trim().ToUpperInvariant() switch
    { "A" => EvidenceLevel.A, "B" => EvidenceLevel.B, "C" => EvidenceLevel.C, "D" => EvidenceLevel.D, _ => EvidenceLevel.U };

    void Show(ObjectLedger.Row r)
    {
        var plan = Parse(r.PlanEvidence); var sec = Parse(r.SectionEvidence);
        bar.color = EvidenceColors.Of(plan);
        var sb = new StringBuilder();
        sb.AppendLine($"<b>{r.Name}</b>");
        sb.AppendLine($"位置・平面: {r.PlanEvidence}({EvidenceColors.Label(plan)})   断面・高さ: {r.SectionEvidence}({EvidenceColors.Label(sec)})");
        var dims = new StringBuilder();
        if (!string.IsNullOrEmpty(r.Height)) dims.Append($"高さ {r.Height} m  ");
        if (!string.IsNullOrEmpty(r.Depth)) dims.Append($"深さ {r.Depth} m  ");
        if (!string.IsNullOrEmpty(r.GroundTp)) dims.Append($"地盤 T.P.{r.GroundTp} m");
        if (dims.Length > 0) sb.AppendLine(dims.ToString());
        if (!string.IsNullOrEmpty(r.Note)) sb.AppendLine(r.Note);
        text.supportRichText = true; text.text = sb.ToString();
    }
}
