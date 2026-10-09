using UnityEngine;

public enum EvidenceLevel { Confirmed, Estimated, Speculative }

public static class EvidenceColors
{
    // 色だけに頼らないよう、UI側でラベル(確実/推定/想像)も併記すること
    public static Color Of(EvidenceLevel level) => level switch
    {
        EvidenceLevel.Confirmed => new Color(0.20f, 0.55f, 0.85f),
        EvidenceLevel.Estimated => new Color(0.95f, 0.65f, 0.15f),
        _ => new Color(0.75f, 0.30f, 0.45f),
    };

    public static string Label(EvidenceLevel level) => level switch
    {
        EvidenceLevel.Confirmed => "確実(遺構)",
        EvidenceLevel.Estimated => "推定(文献・絵図)",
        _ => "想像",
    };
}
