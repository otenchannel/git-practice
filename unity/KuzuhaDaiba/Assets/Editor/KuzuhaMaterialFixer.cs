using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

// 楠葉台場モデル(Assets/Private/kuzuha_*.obj)のマテリアルを URP/Lit で自動生成し、色と地形テクスチャを割り当てる。
//  - エディタ起動/コンパイル時に Assets/Private/Materials/ へ全マテリアルを作成
//  - kuzuha_*.obj のインポート時に同名マテリアルを自動で割り当て(Reimportで反映)
//  - メニュー Kuzuha > Fix Materials : シーン内の kuzuha_* を直接更新(選択不要)
public class KuzuhaMaterialFixer : AssetPostprocessor
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
        {"ev_terrain", Color.white}, {"nat_terrain", Color.white},
    };

    [InitializeOnLoadMethod]
    static void OnLoad() { EditorApplication.delayCall += EnsureAll; }

    static void EnsureAll()
    {
        if (!AssetDatabase.IsValidFolder("Assets/Private")) return;
        if (!AssetDatabase.IsValidFolder(MatDir)) AssetDatabase.CreateFolder("Assets/Private", "Materials");
        foreach (var k in Colors.Keys) GetOrCreate(k);
        AssetDatabase.SaveAssets();
    }

    // インポート時: OBJのマテリアルを自作マテリアルに差し替える
    Material OnAssignMaterialModel(Material material, Renderer renderer)
    {
        if (!assetPath.Contains("kuzuha_")) return null;
        string name = material.name.Replace(" (Instance)", "");
        return Colors.ContainsKey(name) ? AssetDatabase.LoadAssetAtPath<Material>($"{MatDir}/{name}.mat") : null;
    }

    [MenuItem("Kuzuha/Fix Materials")]
    static void Fix()
    {
        EnsureAll();
        int n = 0, miss = 0;
        foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
        {
            if (!IsKuzuha(r.transform)) continue;
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++)
            {
                if (mats[i] == null) continue;
                string name = mats[i].name.Replace(" (Instance)", "");
                if (!Colors.ContainsKey(name)) { miss++; Debug.LogWarning("Kuzuha: 未対応のマテリアル名 " + name); continue; }
                mats[i] = GetOrCreate(name); n++;
            }
            r.sharedMaterials = mats;
        }
        AssetDatabase.SaveAssets();
        Debug.Log($"Kuzuha: {n} スロット更新 / 未対応 {miss}");
        if (n == 0) Debug.LogWarning("Kuzuha: 対象が見つかりません。Hierarchyにkuzuha_*モデルがあるか確認してください");
    }

    static bool IsKuzuha(Transform t)
    {
        for (; t != null; t = t.parent) if (t.name.StartsWith("kuzuha_")) return true;
        return false;
    }

    static Material GetOrCreate(string name)
    {
        string path = $"{MatDir}/{name}.mat";
        var m = AssetDatabase.LoadAssetAtPath<Material>(path);
        var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
        if (m == null) { m = new Material(shader) { name = name }; AssetDatabase.CreateAsset(m, path); }
        m.shader = shader;
        var c = Colors[name];
        m.SetColor("_BaseColor", c); m.SetColor("_Color", c);
        if (name.EndsWith("_terrain"))
        {
            string png = name.StartsWith("ev") ? "kuzuha_provisional_terrain" : "kuzuha_natural_terrain";
            var guids = AssetDatabase.FindAssets(png + " t:Texture2D");
            if (guids.Length > 0)
            {
                var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(AssetDatabase.GUIDToAssetPath(guids[0]));
                m.SetTexture("_BaseMap", tex); m.SetTexture("_MainTex", tex);
            }
            else Debug.LogWarning(png + ".png が見つかりません");
        }
        m.SetFloat("_Smoothness", 0f);
        EditorUtility.SetDirty(m);
        return m;
    }
}
