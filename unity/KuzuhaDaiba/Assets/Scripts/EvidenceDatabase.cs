using System.Collections.Generic;
using System.IO;
using UnityEngine;

// StreamingAssets/evidence.csv(data/evidence.csv のコピー)を読み込む
// 列: element,description,evidence_level,source_ids,note
// 注意: 簡易CSVパーサ。値にカンマや改行を含めない運用とする
public class EvidenceDatabase : MonoBehaviour
{
    public struct Entry
    {
        public string Element, Description, SourceIds, Note;
        public EvidenceLevel Level;
    }

    public static EvidenceDatabase Instance { get; private set; }
    readonly Dictionary<string, Entry> entries = new();

    void Awake()
    {
        Instance = this;
        var path = Path.Combine(Application.streamingAssetsPath, "evidence.csv");
        if (!File.Exists(path)) { Debug.LogError($"evidence.csv not found: {path}"); return; }
        var lines = File.ReadAllLines(path);
        for (int i = 1; i < lines.Length; i++)
        {
            var c = lines[i].Split(',');
            if (c.Length < 5) continue;
            entries[c[0]] = new Entry
            {
                Element = c[0], Description = c[1], SourceIds = c[3], Note = c[4],
                Level = c[2].Trim().ToLowerInvariant() switch
                {
                    "confirmed" => EvidenceLevel.Confirmed,
                    "estimated" => EvidenceLevel.Estimated,
                    _ => EvidenceLevel.Speculative,
                },
            };
        }
    }

    public bool TryGet(string element, out Entry entry) => entries.TryGetValue(element, out entry);
}
