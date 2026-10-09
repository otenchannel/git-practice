using UnityEngine;

// 復元モデルに付ける。element は evidence.csv の element 列と一致させる
[RequireComponent(typeof(Renderer))]
public class EvidenceTag : MonoBehaviour
{
    public string element;
    public bool showEvidenceColor;

    Renderer rend;
    Color original;

    void Start()
    {
        rend = GetComponent<Renderer>();
        original = rend.material.color;
        Apply();
    }

    public void SetShowEvidenceColor(bool on) { showEvidenceColor = on; Apply(); }

    void Apply()
    {
        if (rend == null) return;
        if (showEvidenceColor && EvidenceDatabase.Instance != null
            && EvidenceDatabase.Instance.TryGet(element, out var e))
            rend.material.color = EvidenceColors.Of(e.Level);
        else
            rend.material.color = original;
    }
}
