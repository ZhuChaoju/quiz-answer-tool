using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;

namespace QuizAnswerTool.Core;

/// <summary>题库：加载 + 三级匹配（精确 → 子串 → 模糊 0.85），兼容现有 questions.json 格式。</summary>
public sealed class QuestionBank
{
    private readonly List<Dictionary<string, object?>> _raw;
    private readonly List<(string Key, Dictionary<string, object?> Q)> _index;

    private QuestionBank(List<Dictionary<string, object?>> questions)
    {
        _raw = questions;
        _index = questions
            .Select(q => (Normalize(q.GetValueOrDefault("question")?.ToString() ?? ""), q))
            .ToList();
    }

    public int Count => _raw.Count;

    public static QuestionBank Load(string path)
    {
        var json = File.ReadAllText(path, Encoding.UTF8);
        var items = JsonSerializer.Deserialize<List<Dictionary<string, object?>>>(json)
                    ?? throw new InvalidOperationException("题库格式错误");
        return new QuestionBank(items);
    }

    public static string Normalize(string text)
    {
        if (string.IsNullOrEmpty(text)) return "";
        var sb = new StringBuilder(text.Length);
        foreach (var ch in text)
        {
            // 全角转半角
            if (ch >= '０' && ch <= '９') { sb.Append((char)(ch - '０' + '0')); continue; }
            if (ch >= 'ａ' && ch <= 'ｚ') { sb.Append((char)(ch - 'ａ' + 'a')); continue; }
            if (ch >= 'Ａ' && ch <= 'Ｚ') { sb.Append((char)(ch - 'Ａ' + 'A')); continue; }
            switch (ch)
            {
                case '（': sb.Append('('); continue;
                case '）': sb.Append(')'); continue;
                case '：': sb.Append(':'); continue;
                case '，': sb.Append(','); continue;
                case '。': sb.Append('.'); continue;
                case '！': sb.Append('!'); continue;
                case '？': sb.Append('?'); continue;
            }
            // 去空白与标点（保留中文/字母/数字）
            if (char.IsWhiteSpace(ch)) continue;
            if (!char.IsLetterOrDigit(ch) && ch != '_') continue;
            sb.Append(ch);
        }
        return sb.ToString().ToLowerInvariant();
    }

    public void Add(string question, string answer)
    {
        var key = Normalize(question);
        foreach (var (k, q) in _index)
        {
            if (k == key) { q["answer"] = answer; return; }
        }
        var item = new Dictionary<string, object?>
        {
            ["id"] = _raw.Count + 1,
            ["question"] = question,
            ["options"] = new List<object?>(),
            ["answer"] = answer,
        };
        _raw.Add(item);
        _index.Add((key, item));
    }

    /// <summary>三级匹配：精确 → 子串 → 模糊。threshold 为模糊匹配阈值（默认 0.85）。</summary>
    public Dictionary<string, object?>? Match(string text, double threshold = 0.85)
    {
        // 剥掉“御前科举大赛第X关…题目：”等关卡前缀，避免污染匹配文本
        text = StripQuestionPrefix(text);
        var key = Normalize(text);
        if (string.IsNullOrEmpty(key)) return null;
        foreach (var (k, q) in _index)
            if (k == key) return q;
        foreach (var (k, q) in _index)
            if (k.Contains(key) || key.Contains(k)) return q;
        string? bestKey = null;
        Dictionary<string, object?>? best = null;
        double bestRatio = 0;
        foreach (var (k, q) in _index)
        {
            double ratio = Ratio(key, k);
            if (ratio > bestRatio) { bestRatio = ratio; best = q; bestKey = k; }
        }
        if (best != null && bestRatio >= threshold)
        {
            // 避免短文本误匹配：要求长度接近
            if (Math.Abs(key.Length - bestKey!.Length) <= Math.Max(key.Length, bestKey.Length) / 3)
                return best;
        }
        return null;
    }

    /// <summary>去掉“御前科举大赛第X关…题目：”等关卡前缀，只留题目正文。</summary>
    public static string StripQuestionPrefix(string text)
    {
        int idx = text.IndexOf("题目", StringComparison.Ordinal);
        if (idx >= 0)
        {
            // 去掉“题目”及其前面的关卡信息（保留“题目”后的内容）
            return text[(idx + 2)..];
        }
        return text;
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
