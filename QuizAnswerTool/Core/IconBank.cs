using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace QuizAnswerTool.Core;

/// <summary>看图说话图标库：256 位梯度哈希 → 答案，汉明距离匹配。
/// 未命中时由用户录入答案并连同当前图标哈希入库，越用越全。
/// 注：哈希算法与缩放实现相关，本文件由 C# 版读写，与 Python 版各自的 icons.json 互不混用。</summary>
public sealed class IconBank
{
    private sealed class Entry
    {
        public string Hash { get; set; } = "";
        public string Answer { get; set; } = "";
    }

    private readonly List<Entry> _entries = new();

    /// <summary>256 位哈希：同图标渲染噪声 0~2，不同内容实测 ≥27。</summary>
    public int Threshold { get; set; } = 12;

    public int Count => _entries.Count;

    public static IconBank Load(string path)
    {
        var bank = new IconBank();
        try
        {
            if (!File.Exists(path)) return bank;
            var entries = JsonSerializer.Deserialize<List<Entry>>(File.ReadAllText(path, System.Text.Encoding.UTF8));
            if (entries != null) bank._entries.AddRange(entries);
        }
        catch { /* 损坏时按空库处理 */ }
        return bank;
    }

    public void Save(string path)
    {
        var options = new JsonSerializerOptions
        {
            WriteIndented = true,
            Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        };
        File.WriteAllText(path, JsonSerializer.Serialize(_entries, options), System.Text.Encoding.UTF8);
    }

    /// <summary>256 位梯度哈希：灰度 17x16，逐行比较横向相邻像素（亮→暗记 1），4 段 ulong 拼接。</summary>
    public static string HashIcon(Bitmap bmp)
    {
        const int w = 17, h = 16;
        using var small = new Bitmap(w, h, PixelFormat.Format24bppRgb);
        small.SetResolution(96, 96);
        using (var g = Graphics.FromImage(small))
        {
            g.InterpolationMode = InterpolationMode.HighQualityBilinear;
            g.DrawImage(bmp, new Rectangle(0, 0, w, h));
        }
        var data = small.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        var quads = new ulong[4];   // 256 位 = 4x64,每 64 位进一段
        int bitIdx = 0;
        try
        {
            unsafe
            {
                var stride = data.Stride;
                for (int y = 0; y < h; y++)
                {
                    var row = (byte*)data.Scan0 + y * stride;
                    for (int x = 0; x < w - 1; x++)
                    {
                        // ITU-R BT.601 亮度
                        int l1 = (row[x * 3] * 299 + row[x * 3 + 1] * 587 + row[x * 3 + 2] * 114) / 1000;
                        int l2 = (row[x * 3 + 3] * 299 + row[x * 3 + 4] * 587 + row[x * 3 + 5] * 114) / 1000;
                        if (l1 < l2)
                            quads[bitIdx / 64] |= 1UL << (63 - bitIdx % 64);
                        bitIdx++;
                    }
                }
            }
        }
        finally { small.UnlockBits(data); }
        // x16 = 十六进制最少 16 位（前导补零）；注意 016x 会被当成自定义格式输出十进制
        return $"{quads[0]:x16}{quads[1]:x16}{quads[2]:x16}{quads[3]:x16}";
    }

    private static int Distance(string a, string b)
    {
        if (a.Length != 64 || b.Length != 64) return int.MaxValue;
        int dist = 0;
        for (int i = 0; i < 4; i++)
        {
            ulong x, y;
            try
            {
                x = Convert.ToUInt64(a.Substring(i * 16, 16), 16);
                y = Convert.ToUInt64(b.Substring(i * 16, 16), 16);
            }
            catch (FormatException) { return int.MaxValue; }
            dist += System.Numerics.BitOperations.PopCount(x ^ y);
        }
        return dist;
    }

    /// <summary>最近哈希距离 ≤ Threshold 时返回其答案，否则 null。</summary>
    public string? Match(string iconHash)
    {
        string? bestAnswer = null;
        int best = int.MaxValue;
        foreach (var e in _entries)
        {
            if (e.Hash.Length == 0) continue;
            int d = Distance(iconHash, e.Hash);
            if (d < best) { best = d; bestAnswer = e.Answer; }
        }
        return best <= Threshold && !string.IsNullOrEmpty(bestAnswer) ? bestAnswer : null;
    }

    /// <summary>收录一条图标答案（同哈希已存在时更新答案）。</summary>
    public void Add(string iconHash, string answer)
    {
        var hit = _entries.FirstOrDefault(e => e.Hash == iconHash);
        if (hit != null) { hit.Answer = answer; return; }
        _entries.Add(new Entry { Hash = iconHash, Answer = answer });
    }
}
