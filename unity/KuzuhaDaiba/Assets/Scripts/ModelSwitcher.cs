using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.XR;
using XRUsages = UnityEngine.XR.CommonUsages;

// 根拠色分け版(kuzuha_provisional)と自然色版(kuzuha_natural)を切り替える
// 操作: キーボード Tab / VR 右コントローラの A ボタン(primaryButton)
public class ModelSwitcher : MonoBehaviour
{
    public GameObject evidenceModel;
    public GameObject naturalModel;
    public bool startWithEvidence = true;

    bool evidenceOn;
    bool prevButton;

    public bool EvidenceOn => evidenceOn;

    void Start() { Set(startWithEvidence); }

    void Update()
    {
        bool pressed = Keyboard.current != null && Keyboard.current.tabKey.wasPressedThisFrame;
        var dev = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
        bool b = dev.isValid && dev.TryGetFeatureValue(XRUsages.primaryButton, out var v) && v;
        if (b && !prevButton) pressed = true;
        prevButton = b;
        if (pressed) Set(!evidenceOn);
    }

    public void Set(bool evidence)
    {
        evidenceOn = evidence;
        if (evidenceModel == null || naturalModel == null) Debug.LogWarning("ModelSwitcher: evidenceModel / naturalModel が未設定です。Kuzuha > Setup MVP を実行してください");
        else if (evidenceModel == naturalModel) Debug.LogWarning("ModelSwitcher: 2つのモデルが同じオブジェクトを指しています。KuzuhaMVP の Inspector で割り当てを確認してください");
        if (evidenceModel) evidenceModel.SetActive(evidence);
        if (naturalModel && naturalModel != evidenceModel) naturalModel.SetActive(!evidence);
        Debug.Log($"ModelSwitcher: {(evidence ? "根拠色分け版" : "自然色版")}を表示");
    }
}
