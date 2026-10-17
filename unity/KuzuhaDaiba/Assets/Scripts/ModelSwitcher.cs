using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.XR;

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
        bool b = dev.isValid && dev.TryGetFeatureValue(CommonUsages.primaryButton, out var v) && v;
        if (b && !prevButton) pressed = true;
        prevButton = b;
        if (pressed) Set(!evidenceOn);
    }

    public void Set(bool evidence)
    {
        evidenceOn = evidence;
        if (evidenceModel) evidenceModel.SetActive(evidence);
        if (naturalModel) naturalModel.SetActive(!evidence);
    }
}
