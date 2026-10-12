using UnityEngine;

// A=実測確認 / B=史料明示 / C=比較推定 / D=視覚補完 / U=未復元(根拠不足。形を決めない)
public enum EvidenceLevel { A, B, C, D, U }

public static class EvidenceColors
{
    // 色だけに頼らないよう、UI側でラベルも併記すること
    public static Color Of(EvidenceLevel level) => level switch
    {
        EvidenceLevel.A => new Color(0.20f, 0.55f, 0.85f),
        EvidenceLevel.B => new Color(0.25f, 0.70f, 0.50f),
        EvidenceLevel.C => new Color(0.95f, 0.65f, 0.15f),
        EvidenceLevel.D => new Color(0.75f, 0.30f, 0.45f),
        _ => new Color(0.60f, 0.60f, 0.60f),
    };

    public static string Label(EvidenceLevel level) => level switch
    {
        EvidenceLevel.A => "確認済み",
        EvidenceLevel.B => "史料に記載",
        EvidenceLevel.C => "類例から推定",
        EvidenceLevel.D => "仮説/復元演出",
        _ => "資料不足",
    };
}
