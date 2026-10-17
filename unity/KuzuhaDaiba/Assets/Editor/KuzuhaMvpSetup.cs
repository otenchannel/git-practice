using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// メニュー Kuzuha > Setup MVP : MVP に必要な部品をシーンに一括で配置する(何度実行しても重複しない)
//  - 自然色版モデルが無ければ Assets/Private/kuzuha_natural.obj から配置
//  - マテリアル適用(Fix Materials)
//  - ObjectLedger / ModelSwitcher / ModelColliders / InfoPanel を "KuzuhaMVP" に付ける
//  - XR Origin に WalkRig を付け、南虎口の手前(北向き)に置く
public static class KuzuhaMvpSetup
{
    [MenuItem("Kuzuha/Setup MVP")]
    static void Setup()
    {
        var ev = Find("kuzuha_provisional"); var nat = Find("kuzuha_natural");
        if (ev == null && nat == null) { Debug.LogError("Kuzuha: シーンに kuzuha_provisional か kuzuha_natural を置いてから実行してください"); return; }
        if (nat == null) nat = Place("Assets/Private/kuzuha_natural.obj", ev);
        if (ev == null) ev = Place("Assets/Private/kuzuha_provisional.obj", nat);
        EditorApplication.ExecuteMenuItem("Kuzuha/Fix Materials");

        var mvp = GameObject.Find("KuzuhaMVP") ?? new GameObject("KuzuhaMVP");
        Get<ObjectLedger>(mvp);
        var sw = Get<ModelSwitcher>(mvp); sw.evidenceModel = ev; sw.naturalModel = nat;
        var col = Get<ModelColliders>(mvp); col.models = new[] { ev, nat };
        var info = Get<InfoPanel>(mvp); info.switcher = sw;

        var origin = FindRoot("XR Origin");
        if (origin != null)
        {
            var walk = Get<WalkRig>(origin);
            origin.transform.position = new Vector3(18.7f, 30f, -45f); origin.transform.rotation = Quaternion.identity;
            var cam = origin.GetComponentInChildren<Camera>(); if (cam) { walk.head = cam.transform; info.head = cam.transform; }
        }
        else Debug.LogWarning("Kuzuha: XR Origin が見つかりません(歩行・解説パネルは未設定)");

        foreach (var f in new[] { "object-ledger.csv", "features.json" })
            if (!File.Exists(Path.Combine(Application.streamingAssetsPath, f)))
                Debug.LogWarning($"Kuzuha: Assets/StreamingAssets/{f} がありません。送った {f} を入れてください(解説表示に必要)");
        EditorSceneManager.MarkSceneDirty(mvp.scene);
        Debug.Log("Kuzuha: MVP を配置しました。再生して Tab(VRは右Aボタン)で色分け⇔自然色を切り替えられます");
    }

    static GameObject Find(string prefix)
    {
        foreach (var go in Object.FindObjectsByType<Transform>(FindObjectsSortMode.None)) if (go.parent == null && go.name.StartsWith(prefix)) return go.gameObject;
        return null;
    }

    static GameObject FindRoot(string prefix) => Find(prefix);

    static GameObject Place(string path, GameObject like)
    {
        var asset = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (asset == null) { Debug.LogError("Kuzuha: " + path + " がありません"); return null; }
        var go = (GameObject)PrefabUtility.InstantiatePrefab(asset);
        if (like != null) { go.transform.position = like.transform.position; go.transform.rotation = like.transform.rotation; go.transform.localScale = like.transform.localScale; }
        return go;
    }

    static T Get<T>(GameObject go) where T : Component => go.GetComponent<T>() ?? go.AddComponent<T>();
}
