using System.Text;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.UI;
using UnityEngine.XR;
using XRUsages = UnityEngine.XR.CommonUsages;

// 説明の表示: 見たいところを「クリック」したときだけ出す(普段は何も出さない)。
//  PC   : 画面上の知りたい場所を左クリック。何もない所をクリックするか Esc キーで閉じる。
//  VR   : 右コントローラで指して、右トリガーを押す。何もない所を指して押すと閉じる。
//  土塁・堀は地形メッシュ上のクリック位置から、建物・門などはオブジェクト名から台帳を引く。
// 画面には内部の記号・番号を出さない。根拠は日本語の言葉だけで表示する。
public class InfoPanel : MonoBehaviour
{
    public Transform head;
    public ModelSwitcher switcher;
    public float maxDistance = 150f;
    public float panelDistance = 1.6f;
    public Vector2 panelSize = new Vector2(0.95f, 0.5f);

    Text text; Image bar; Transform panel; LineRenderer laser;
    bool prevTrigger;

    void Start()
    {
        if (head == null && Camera.main != null) head = Camera.main.transform;
        Build();
    }

    void Build()
    {
        var go = new GameObject("InfoPanel"); go.transform.SetParent(head, false);
        var cv = go.AddComponent<Canvas>(); cv.renderMode = RenderMode.WorldSpace;
        panel = go.transform;  // Canvas追加で Transform が RectTransform に置き換わるため取り直す
        panel.localPosition = new Vector3(0f, -0.26f, panelDistance); panel.localScale = Vector3.one * 0.001f;
        go.GetComponent<RectTransform>().sizeDelta = panelSize * 1000f;
        var bg = new GameObject("bg").AddComponent<Image>(); bg.transform.SetParent(panel, false); bg.color = new Color(0, 0, 0, 0.72f);
        var brt = bg.rectTransform; brt.anchorMin = Vector2.zero; brt.anchorMax = Vector2.one; brt.offsetMin = brt.offsetMax = Vector2.zero;
        bar = new GameObject("bar").AddComponent<Image>(); bar.transform.SetParent(panel, false);
        var rr = bar.rectTransform; rr.anchorMin = new Vector2(0, 0); rr.anchorMax = new Vector2(0, 1); rr.pivot = new Vector2(0, 0.5f); rr.sizeDelta = new Vector2(14, 0); rr.anchoredPosition = Vector2.zero;
        var t = new GameObject("text"); t.transform.SetParent(panel, false);
        text = t.AddComponent<Text>(); text.font = JapaneseFont(); text.fontSize = 34; text.color = Color.white; text.supportRichText = true;
        text.horizontalOverflow = HorizontalWrapMode.Wrap; text.verticalOverflow = VerticalWrapMode.Truncate;
        var trt = text.rectTransform; trt.anchorMin = Vector2.zero; trt.anchorMax = Vector2.one; trt.offsetMin = new Vector2(32, 12); trt.offsetMax = new Vector2(-16, -12);
        panel.gameObject.SetActive(false);
    }

    static Font JapaneseFont()
    {
        var f = Font.CreateDynamicFontFromOSFont(new[] { "Yu Gothic UI", "Meiryo", "Noto Sans CJK JP", "Noto Sans JP", "Droid Sans Fallback", "Arial" }, 34);
        return f != null ? f : Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
    }

    void Update()
    {
        if (head == null || ObjectLedger.Instance == null) return;
        var k = Keyboard.current;
        if (k != null && k.escapeKey.wasPressedThisFrame) Hide();

        // PC: 左クリック(右クリックは見回し用)
        var m = Mouse.current;
        if (m != null && m.leftButton.wasPressedThisFrame && !XRSettings.isDeviceActive && Camera.main != null)
            Pick(Camera.main.ScreenPointToRay(m.position.ReadValue()));

        // VR: 右コントローラの先にレーザーを出し、トリガーで選ぶ
        var dev = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
        if (XRSettings.isDeviceActive && dev.isValid && dev.TryGetFeatureValue(XRUsages.devicePosition, out var pos) && dev.TryGetFeatureValue(XRUsages.deviceRotation, out var rot))
        {
            var space = head.parent != null ? head.parent : head;  // Camera Offset(トラッキング空間)
            var ray = new Ray(space.TransformPoint(pos), space.rotation * rot * Vector3.forward);
            DrawLaser(ray);
            bool trig = dev.TryGetFeatureValue(XRUsages.triggerButton, out var tv) && tv;
            if (trig && !prevTrigger) Pick(ray);
            prevTrigger = trig;
        }
        else if (laser != null) laser.enabled = false;
    }

    void DrawLaser(Ray ray)
    {
        if (laser == null)
        {
            laser = new GameObject("Laser").AddComponent<LineRenderer>(); laser.transform.SetParent(transform, false);
            laser.positionCount = 2; laser.widthMultiplier = 0.004f; laser.material = new Material(Shader.Find("Sprites/Default")); laser.startColor = laser.endColor = new Color(1, 1, 1, 0.6f);
        }
        laser.enabled = true;
        laser.SetPosition(0, ray.origin);
        laser.SetPosition(1, Physics.Raycast(ray, out var h, maxDistance, ~0, QueryTriggerInteraction.Ignore) ? h.point : ray.origin + ray.direction * 5f);
    }

    void Pick(Ray ray)
    {
        ObjectLedger.Row row = null;
        if (Physics.Raycast(ray, out var hit, maxDistance, ~0, QueryTriggerInteraction.Ignore))
        {
            row = ObjectLedger.Instance.FindByObjectName(hit.collider.name) ?? ObjectLedger.Instance.FindByPosition(hit.point);
        }
        if (row == null) Hide(); else Show(row);
    }

    void Hide() { if (panel != null) panel.gameObject.SetActive(false); }

    static EvidenceLevel Parse(string s) => (s ?? "").Trim().ToUpperInvariant() switch
    { "A" => EvidenceLevel.A, "B" => EvidenceLevel.B, "C" => EvidenceLevel.C, "D" => EvidenceLevel.D, _ => EvidenceLevel.U };

    void Show(ObjectLedger.Row r)
    {
        var plan = Parse(r.PlanEvidence); var sec = Parse(r.SectionEvidence);
        bar.color = EvidenceColors.Of(plan);
        var sb = new StringBuilder();
        sb.AppendLine($"<b>{r.Name}</b>");
        var desc = ObjectDescriptions.Of(r.Id);
        if (!string.IsNullOrEmpty(desc)) sb.AppendLine(desc);
        var dims = new StringBuilder();
        if (!string.IsNullOrEmpty(r.Height)) dims.Append($"高さ 約{r.Height} m   ");
        if (!string.IsNullOrEmpty(r.Depth)) dims.Append($"深さ 約{r.Depth} m   ");
        if (dims.Length > 0) sb.AppendLine(dims.ToString());
        sb.AppendLine($"<size=28>位置・形の根拠: {EvidenceColors.Label(plan)}   高さ・断面の根拠: {EvidenceColors.Label(sec)}</size>");
        text.text = sb.ToString();
        panel.gameObject.SetActive(true);
    }
}
