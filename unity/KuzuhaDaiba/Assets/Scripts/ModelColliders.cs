using UnityEngine;

// モデル(kuzuha_provisional / kuzuha_natural)の全メッシュに MeshCollider を付ける。歩行の接地とレイキャスト用
public class ModelColliders : MonoBehaviour
{
    public GameObject[] models;

    void Awake()
    {
        foreach (var m in models)
        {
            if (m == null) continue;
            foreach (var mf in m.GetComponentsInChildren<MeshFilter>(true))
                if (mf.GetComponent<Collider>() == null) mf.gameObject.AddComponent<MeshCollider>().sharedMesh = mf.sharedMesh;
        }
    }
}
