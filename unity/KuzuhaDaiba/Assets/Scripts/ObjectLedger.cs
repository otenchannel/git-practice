using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

// StreamingAssets/object-ledger.csv と features.json を読み込む(どちらも data/private/geo/vec/ で生成。gitには入れない)
// 座標: Unity の X=東, Z=北, Y=標高(川の縁=5.0m T.P. を 0)
public class ObjectLedger : MonoBehaviour
{
    public class Row
    {
        public string Id, Name, Kind, PlanEvidence, SectionEvidence, Note;
        public string SpecNo, Height, Depth, GroundTp;
    }

    [Serializable] class Feat { public string id; public string kind; public float[] xz; }
    [Serializable] class FeatList { public Feat[] features; }

    public static ObjectLedger Instance { get; private set; }
    public readonly Dictionary<string, Row> Rows = new();
    readonly List<(string id, Vector2[] poly, bool earth)> feats = new();

    void Awake()
    {
        Instance = this;
        var dir = Application.streamingAssetsPath;
        var csv = Path.Combine(dir, "object-ledger.csv");
        if (File.Exists(csv)) LoadCsv(File.ReadAllText(csv, Encoding.UTF8)); else Debug.LogWarning("object-ledger.csv がありません: " + csv);
        var js = Path.Combine(dir, "features.json");
        if (File.Exists(js))
        {
            foreach (var f in JsonUtility.FromJson<FeatList>(File.ReadAllText(js, Encoding.UTF8)).features)
            {
                var p = new Vector2[f.xz.Length / 2];
                for (int i = 0; i < p.Length; i++) p[i] = new Vector2(f.xz[2 * i], f.xz[2 * i + 1]);
                feats.Add((f.id, p, f.kind == "earthwork"));
            }
        }
        else Debug.LogWarning("features.json がありません: " + js);
    }

    void LoadCsv(string text)
    {
        var table = ParseCsv(text);
        if (table.Count < 2) return;
        var h = table[0]; int Col(string n) => Array.IndexOf(h.ToArray(), n);
        int iId = Col("id"), iName = Col("name"), iKind = Col("kind"), iSpec = Col("spec_no"), iPe = Col("plan_evidence"), iSe = Col("section_evidence"),
            iH = Col("height_m"), iD = Col("depth_m"), iNote = Col("note"), iG = Col("ground_tp_m");
        string At(List<string> r, int i) => i >= 0 && i < r.Count ? r[i] : "";
        for (int k = 1; k < table.Count; k++)
        {
            var r = table[k]; if (r.Count < 3) continue;
            Rows[At(r, iId)] = new Row
            {
                Id = At(r, iId), Name = At(r, iName), Kind = At(r, iKind), SpecNo = At(r, iSpec), PlanEvidence = At(r, iPe), SectionEvidence = At(r, iSe),
                Height = At(r, iH), Depth = At(r, iD), Note = At(r, iNote), GroundTp = At(r, iG),
            };
        }
    }

    // 引用符つきフィールド・フィールド内の改行に対応する CSV パーサ
    static List<List<string>> ParseCsv(string s)
    {
        var rows = new List<List<string>>(); var row = new List<string>(); var sb = new StringBuilder(); bool q = false;
        for (int i = 0; i < s.Length; i++)
        {
            char c = s[i];
            if (q)
            {
                if (c == '"') { if (i + 1 < s.Length && s[i + 1] == '"') { sb.Append('"'); i++; } else q = false; }
                else sb.Append(c);
            }
            else if (c == '"') q = true;
            else if (c == ',') { row.Add(sb.ToString()); sb.Clear(); }
            else if (c == '\n' || c == '\r')
            {
                if (c == '\r' && i + 1 < s.Length && s[i + 1] == '\n') i++;
                row.Add(sb.ToString()); sb.Clear();
                if (row.Count > 1 || row[0] != "") rows.Add(row);
                row = new List<string>();
            }
            else sb.Append(c);
        }
        if (sb.Length > 0 || row.Count > 0) { row.Add(sb.ToString()); rows.Add(row); }
        return rows;
    }

    // オブジェクト名(例: gate_E_post1)から台帳の行を探す。最も長く一致する id を採用する
    public Row FindByObjectName(string objName)
    {
        Row best = null;
        foreach (var kv in Rows)
            if (objName.StartsWith(kv.Key, StringComparison.Ordinal) && (best == null || kv.Key.Length > best.Id.Length)) best = kv.Value;
        return best;
    }

    // 地面上の点(Unity座標)が、どの土塁・堀の足元に入るか。土塁を優先する
    public Row FindByPosition(Vector3 p)
    {
        var pt = new Vector2(p.x, p.z); string hit = null;
        foreach (var f in feats)
            if (Inside(f.poly, pt)) { if (f.earth) { hit = f.id; break; } hit ??= f.id; }
        return hit != null && Rows.TryGetValue(hit, out var r) ? r : null;
    }

    static bool Inside(Vector2[] poly, Vector2 p)
    {
        bool c = false;
        for (int i = 0, j = poly.Length - 1; i < poly.Length; j = i++)
            if (((poly[i].y > p.y) != (poly[j].y > p.y)) && (p.x < (poly[j].x - poly[i].x) * (p.y - poly[i].y) / (poly[j].y - poly[i].y) + poly[i].x)) c = !c;
        return c;
    }
}
