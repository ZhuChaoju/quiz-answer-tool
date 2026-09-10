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

    /// <summary>选项范围模板匹配：实况图标截图 vs 各选项素材图,亮度归一化互相关(NCC)最大者胜。
    /// NCC 对游戏渲染与素材图的亮度/对比差异鲁棒(MSE 实测两者差异普遍在万级,区分度不足)。
    /// 实况图取中央 76% 区域比较(边缘是对话框背景)。返回全部候选 (名, ncc) 按 ncc 降序。</summary>
    public static List<(string Name, double Ncc)> OptionMatchAll(
        Bitmap live, IEnumerable<string> optionNames, string assetDir)
    {
        const int S = 64;   // 统一缩放尺寸
        const int inset = S * 12 / 100;   // 实况图边缘 12% 为对话框背景,比较时剔除
        var results = new List<(string, double)>();

        // 实况图边缘中位色:素材透明底的合成色(与实况背景一致,NCC 才能同向比较)
        var probe = new Bitmap(live, S, S);
        int[] border = new int[4 * S * 2];
        int bi = 0;
        for (int x = 0; x < S; x++)
        {
            border[bi++] = probe.GetPixel(x, 0).ToArgb();
            border[bi++] = probe.GetPixel(x, S - 1).ToArgb();
            border[bi++] = probe.GetPixel(0, x).ToArgb();
            border[bi++] = probe.GetPixel(S - 1, x).ToArgb();
        }
        var bg = Color.FromArgb(border[bi / 2]);
        probe.Dispose();

        double[] LiveVec()
        {
            using var ls = new Bitmap(live, S, S);
            var bd = ls.LockBits(new Rectangle(0, 0, S, S), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            var v = new double[(S - 2 * inset) * (S - 2 * inset)];
            try
            {
                unsafe
                {
                    int i = 0;
                    for (int y = inset; y < S - inset; y++)
                    {
                        var row = (byte*)bd.Scan0 + y * bd.Stride;
                        for (int x = inset; x < S - inset; x++)
                            v[i++] = row[x * 4] * 299 + row[x * 4 + 1] * 587 + row[x * 4 + 2] * 114;
                    }
                }
            }
            finally { ls.UnlockBits(bd); }
            return v;
        }

        double[] AssetVec(string path)
        {
            using var asset = Image.FromFile(path) as Bitmap ?? new Bitmap(path);
            using var canvas = new Bitmap(S, S, PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(canvas))
            {
                g.Clear(bg);   // 垫实况背景色,亮度关系与实况一致
                g.InterpolationMode = InterpolationMode.HighQualityBilinear;
                g.DrawImage(asset, 0, 0, S, S);
            }
            var ad2 = canvas.LockBits(new Rectangle(0, 0, S, S), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            var v = new double[(S - 2 * inset) * (S - 2 * inset)];
            try
            {
                unsafe
                {
                    int i = 0;
                    for (int y = inset; y < S - inset; y++)
                    {
                        var row = (byte*)ad2.Scan0 + y * ad2.Stride;
                        for (int x = inset; x < S - inset; x++)
                            v[i++] = row[x * 4] * 299 + row[x * 4 + 1] * 587 + row[x * 4 + 2] * 114;
                    }
                }
            }
            finally { canvas.UnlockBits(ad2); }
            return v;
        }

        static double Ncc(double[] a, double[] b)
        {
            double ma = 0, mb = 0;
            for (int i = 0; i < a.Length; i++) { ma += a[i]; mb += b[i]; }
            ma /= a.Length; mb /= b.Length;
            double num = 0, da = 0, db = 0;
            for (int i = 0; i < a.Length; i++)
            {
                double xa = a[i] - ma, xb = b[i] - mb;
                num += xa * xb; da += xa * xa; db += xb * xb;
            }
            double den = Math.Sqrt(da * db);
            return den > 0 ? num / den : 0;
        }

        var lv = LiveVec();
        foreach (var name in optionNames.Distinct())
        {
            if (string.IsNullOrWhiteSpace(name)) continue;
            var path = Path.Combine(assetDir, name.Trim() + ".png");
            if (!File.Exists(path)) continue;
            try { results.Add((name.Trim(), Ncc(lv, AssetVec(path)))); }
            catch { /* 单个素材损坏跳过 */ }
        }
        return results.OrderByDescending(r => r.Item2).ToList();
    }
}
