using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.XR;
using XRUsages = UnityEngine.XR.CommonUsages;

// 現地スケールで歩く。XR Origin に付ける。
//  VR: 左スティックで移動(頭の向き基準)、右スティック左右でスナップ回転
//  デスクトップ: WASD 移動、Shift で走る、右クリック押下中にマウスで見回す
// 高さは真下へのレイキャストで地面に合わせる(モデルにコライダーが必要: ModelColliders)
public class WalkRig : MonoBehaviour
{
    public Transform head;            // Main Camera(未指定なら Camera.main)
    public float walkSpeed = 1.4f;    // m/s
    public float runSpeed = 4.0f;
    public float eyeHeight = 1.6f;    // デスクトップ時の目の高さ
    public float snapDegrees = 30f;
    public LayerMask groundMask = ~0;

    float yaw, pitch, snapCooldown;

    void Start()
    {
        if (head == null && Camera.main != null) head = Camera.main.transform;
        yaw = transform.eulerAngles.y;
    }

    void Update()
    {
        if (head == null) return;
        Vector2 move = Vector2.zero; float speed = walkSpeed; float turn = 0f;
        bool vr = XRSettings.isDeviceActive;

        var k = Keyboard.current;
        if (k != null)
        {
            if (k.wKey.isPressed) move.y += 1;
            if (k.sKey.isPressed) move.y -= 1;
            if (k.dKey.isPressed) move.x += 1;
            if (k.aKey.isPressed) move.x -= 1;
            if (k.leftShiftKey.isPressed) speed = runSpeed;
        }
        var left = InputDevices.GetDeviceAtXRNode(XRNode.LeftHand);
        if (left.isValid && left.TryGetFeatureValue(XRUsages.primary2DAxis, out var a) && a.sqrMagnitude > 0.04f) move += a;
        var right = InputDevices.GetDeviceAtXRNode(XRNode.RightHand);
        if (right.isValid && right.TryGetFeatureValue(XRUsages.primary2DAxis, out var r)) turn = r.x;

        if (!vr)
        {
            var m = Mouse.current;
            if (m != null && m.rightButton.isPressed)
            {
                var d = m.delta.ReadValue() * 0.1f; yaw += d.x; pitch = Mathf.Clamp(pitch - d.y, -80f, 80f);
                transform.rotation = Quaternion.Euler(0, yaw, 0); head.localRotation = Quaternion.Euler(pitch, 0, 0);
            }
        }
        else
        {
            snapCooldown -= Time.deltaTime;
            if (Mathf.Abs(turn) > 0.7f && snapCooldown <= 0f) { transform.RotateAround(head.position, Vector3.up, Mathf.Sign(turn) * snapDegrees); snapCooldown = 0.35f; }
        }

        var fwd = Vector3.ProjectOnPlane(head.forward, Vector3.up).normalized;
        var rgt = Vector3.ProjectOnPlane(head.right, Vector3.up).normalized;
        var delta = (fwd * move.y + rgt * move.x) * speed * Time.deltaTime;
        transform.position += new Vector3(delta.x, 0, delta.z);
        SnapToGround(vr);
    }

    void SnapToGround(bool vr)
    {
        var from = new Vector3(head.position.x, 400f, head.position.z);
        if (Physics.Raycast(from, Vector3.down, out var hit, 800f, groundMask, QueryTriggerInteraction.Ignore))
        {
            // Origin の Y を地面に合わせる(VRは床=地面。デスクトップは目の高さを別途与える)
            var p = transform.position; p.y = hit.point.y; transform.position = p;
            if (!vr) head.localPosition = new Vector3(head.localPosition.x, eyeHeight, head.localPosition.z);
        }
    }
}
