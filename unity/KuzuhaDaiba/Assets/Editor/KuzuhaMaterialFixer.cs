using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

// Hierarchyで選択したモデル(kuzuha_provisional / kuzuha_natural)の全マテリアルを
// URP/Lit で作り直し、色と地形テクスチャを自動で割り当てる。
// メニュー: Kuzuha > Fix Materials (選択中のモデル)
public static class KuzuhaMaterialFixer
{
    const string MatDir = "Assets/Private/Materials";

    static readonly Dictionary<string, Color> Colors = new Dictionary<string, Color>
    {
        {"ground", new Color(0.80f,0.78f,0.72f)}, {"earth_C", new Color(0.95f,0.65f,0.15f)},
        {"moat_C", new Color(0.25f,0.55f,0.85f)}, {"moat_U", new Color(0.55f,0.62f,0.70f)},
        {"earth_U", new Color(0.70f,0.70f,0.70f)}, {"bridge_D", new Color(0.85f,0.45f,0.60f)},
        {"obj_D", new Color(0.75f,0.30f,0.45f)}, {"nat_dirt", new Color(0.52f,0.42f,0.30f)},
        {"nat_stone", new Color(0.58f,0.58f,0.56f)}, {"nat_wood", new Color(0.38f,0.26f,0.17f)},
        {"nat_roof", new Color(0.24f,0.24f,0.27f)}, {"nat_plaster", new Color(0.84f,0.81f,0.74f)},
    };

    [MenuItem("Kuzuha/Fix Materials (選択中のモデル)")]
    static void Fix()
    {
        var go = Selection.activeGameObject;
        if (go == null) { Debug.LogWarning("Hierarchyでkuzuha_*モデルを選択してください"); return; }
        Directory.CreateDirectory(MatDir);
        var shader = Shader.Find("Universal Render Pipeline/Lit");
        int n = 0;
        foreach (var r in go.GetComponentsInChildren<Renderer>(true))
        {
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++)
            {
                if (mats[i] == null) continue;
                string name = mats[i].name.Replace(" (Instance)", "");
                var m = GetOrCreate(name, shader);
                if (m != null) { mats[i] = m; n++; }
            }
            r.sharedMaterials = mats;
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"Kuzuha: {n} 個のマテリアルスロットを更新しました");
    }

    static Material GetOrCreate(string name, Shader shader)
    {
        string path = $"{MatDir}/{name}.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (m == null) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
        m.shader = shader;
        if (name.EndsWith("_terrain"))
        {
            // ev_terrain -> kuzuha_provisional_terrain.png, nat_terrain -> kuzuha_natural_terrain.png
            string png = name.StartsWith("ev") ? "kuzuha_provisional_terrain" : "kuzuha_natural_terrain";
            var guids = AssetDatabase.FindAssets(png + " t:Texture2D");
            if (guids.Length == 0) { Debug.LogWarning(png + ".png が見つかりません"); return m; }
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(AssetDatabase.GUIDToAssetPath(guids[0]));
            m.SetTexture("_BaseMap", tex);
            m.SetColor("_BaseColor", Color.white);
        }
        else if (Colors.TryGetValue(name, out var c)) m.SetColor("_BaseColor", c);
        m.SetFloat("_Smoothness", 0f);
        EditorUtility.SetDirty(m);
        return m;
    }
}
