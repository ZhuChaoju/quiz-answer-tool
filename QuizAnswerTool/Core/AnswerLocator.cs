using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace QuizAnswerTool.Core;

/// <summary>答案行定位：在选项行中找答案，返回 (行, 答案在行内的左右比例)。</summary>
public static class AnswerLocator
{
    private static readonly Regex PrefixRe = new(@"^[A-Za-z一二三四五六七八九十百\d]+[、.．:：]\s*", RegexOptions.Compiled);

    /// <summary>答案可能含 "/" 分隔的多段（如 "及时好雨润新绿／送暖春风过万家"），任一命中即可。</summary>
    public static (OcrLine Line, double Left, double Right)? Find(List<OcrLine> lines, string answer)
    {
        answer = answer.Trim();
        if (string.IsNullOrEmpty(answer)) return null;
        var parts = Regex.Split(answer, "[/／]")
            .Select(p => p.Trim()).Where(p => p.Length > 0).ToList();
        foreach (var ln in lines)
        {
            var text = Clean(ln.Text);
            if (string.IsNullOrEmpty(text)) continue;
            foreach (var part in parts)
            {
                if (part == text || text.Contains(part) || part.Contains(text))
                {
                    var (l, r) = SegmentBounds(ln, part);
                    return (ln, l, r);
                }
            }
        }
        // 模糊兜底
        OcrLine? best = null;
        double bestRatio = 0;
        foreach (var ln in lines)
        {
            var text = Clean(ln.Text);
            if (string.IsNullOrEmpty(text)) continue;
            double ratio = parts.Max(p => Ratio(p, text));
            if (ratio > bestRatio) { bestRatio = ratio; best = ln; }
        }
        return best != null && bestRatio >= 0.7 ? (best, 0.0, 1.0) : null;
    }

    private static string Clean(string text)
    {
        text = text.Trim();
        var m = PrefixRe.Match(text);
        return m.Success ? text[m.Length..] : text;
    }

    /// <summary>段坐标优先；跨段拼接取最窄覆盖；无段信息退化字符比例。</summary>
    private static (double, double) SegmentBounds(OcrLine line, string part)
    {
        if (line.Segments.Count > 0)
        {
            int n = line.Segments.Count;
            for (int i = 0; i < n; i++)
            {
                var (segText, segLeft, segRight) = line.Segments[i];
                if (segText.Contains(part) || part.Contains(segText))
                    return (segLeft, segRight);
            }
            (double, double)? best = null;
            for (int i = 0; i < n; i++)
            {
                var combined = line.Segments[i].Text;
                for (int j = i; j < n; j++)
                {
                    if (j > i) combined += line.Segments[j].Text;
                    if (combined.Contains(part) || part.Contains(combined))
                    {
                        var span = (line.Segments[i].Left, line.Segments[j].Right);
                        if (best == null || span.Item2 - span.Item1 < best.Value.Item2 - best.Value.Item1)
                            best = span;
                    }
                }
            }
            if (best != null) return best.Value;
        }
        int idx = line.Text.IndexOf(part, StringComparison.Ordinal);
        if (idx >= 0)
            return ((double)idx / Math.Max(line.Text.Length, 1), (double)(idx + part.Length) / Math.Max(line.Text.Length, 1));
        return (0.0, 1.0);
    }

    private static double Ratio(string a, string b)
    {
        // SequenceMatcher 风格：递归最长匹配块（对单个错字/漏字更宽容，与 Python 一致）
        int m = a.Length, n = b.Length;
        if (m == 0 || n == 0) return 0;
        var memo = new Dictionary<(int, int, int, int), int>();
        int MatchBlocks(int a1, int a2, int b1, int b2)
        {
            var key = (a1, a2, b1, b2);
            if (memo.TryGetValue(key, out var v)) return v;
            int best = 0, bi = -1, bj = -1;
            for (int i = a1; i < a2; i++)
                for (int j = b1; j < b2; j++)
                {
                    if (a[i] == b[j])
                    {
                        int len = 1;
                        while (i + len < a2 && j + len < b2 && a[i + len] == b[j + len]) len++;
                        if (len > best) { best = len; bi = i; bj = j; }
                    }
                }
            if (best == 0) { memo[key] = 0; return 0; }
            int total = best;
            total += MatchBlocks(a1, bi, b1, bj);
            total += MatchBlocks(bi + best, a2, bj + best, b2);
            memo[key] = total;
            return total;
        }
        double matched = MatchBlocks(0, m, 0, n);
        return 2.0 * matched / (m + n);
    }
}
