using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace QuizAnswerTool.Core;

/// <summary>配置文件（兼容原 config.json 格式，新增 question_roi/option_roi 写死区域）。</summary>
public sealed class Config
{
    public double IntervalSec { get; set; } = 0.05;
    public Roi QuestionRoi { get; set; } = new() { X = 28.0, Y = 23.0, W = 55.0, H = 24.0 };
    public Roi OptionRoi { get; set; } = new() { X = 25.0, Y = 44.0, W = 70.0, H = 24.0 };
    /// <summary>看图说话活动：题目图标区（居中技能图标本体）。</summary>
    public Roi PictureIconRoi { get; set; } = new() { X = 43.5, Y = 36.5, W = 13.0, H = 13.0 };
    /// <summary>看图说话活动：选项区（与科举布局不同，独立配置）。</summary>
    public Roi PictureOptionRoi { get; set; } = new() { X = 25.0, Y = 60.0, W = 55.0, H = 18.0 };
    public double Confidence { get; set; } = 0.4;
    public string WindowKeyword { get; set; } = "";
    /// <summary>活动模式：keju=科举文字题（题库匹配）/ picture=看图说话（图标哈希匹配）。</summary>
    public string Activity { get; set; } = "keju";
    /// <summary>OCR 模型档位：tiny（默认，最快）/ small / medium。</summary>
    public string ModelType { get; set; } = "tiny";
    /// <summary>Windows 上启用 DirectML（GPU）推理，需引用 Microsoft.ML.OnnxRuntime.DirectML 包。</summary>
    public bool UseDml { get; set; } = false;

    public static Config Load(string path)
    {
        var cfg = new Config();
        if (!File.Exists(path)) return cfg;
        try
        {
            using var doc = JsonDocument.Parse(File.ReadAllText(path, System.Text.Encoding.UTF8));
            var root = doc.RootElement;
            if (root.TryGetProperty("interval_sec", out var iv)) cfg.IntervalSec = iv.GetDouble();
            if (root.TryGetProperty("confidence", out var cf)) cfg.Confidence = cf.GetDouble();
            if (root.TryGetProperty("window_keyword", out var wk)) cfg.WindowKeyword = wk.GetString() ?? "";
            if (root.TryGetProperty("activity", out var ac)) cfg.Activity = ac.GetString() ?? "keju";
            if (root.TryGetProperty("ocr", out var ocr))
            {
                if (ocr.TryGetProperty("confidence", out var oc)) cfg.Confidence = oc.GetDouble();
                if (ocr.TryGetProperty("model_type", out var om)) cfg.ModelType = om.GetString() ?? "tiny";
                if (ocr.TryGetProperty("use_dml", out var od) && od.ValueKind == JsonValueKind.True) cfg.UseDml = true;
            }
            cfg.QuestionRoi = ParseRoi(root, "question_roi") ?? cfg.QuestionRoi;
            cfg.OptionRoi = ParseRoi(root, "option_roi") ?? cfg.OptionRoi;
            if (root.TryGetProperty("picture", out var pic))
            {
                cfg.PictureIconRoi = ParseRoi(pic, "icon_roi") ?? cfg.PictureIconRoi;
                cfg.PictureOptionRoi = ParseRoi(pic, "option_roi") ?? cfg.PictureOptionRoi;
            }
        }
        catch { /* 配置损坏时用默认 */ }
        if (cfg.Activity != "keju" && cfg.Activity != "picture") cfg.Activity = "keju";
        return cfg;
    }

    private static Roi? ParseRoi(JsonElement root, string name)
    {
        if (!root.TryGetProperty(name, out var roi)) return null;
        return new Roi
        {
            X = roi.GetProperty("x").GetDouble(),
            Y = roi.GetProperty("y").GetDouble(),
            W = roi.GetProperty("w").GetDouble(),
            H = roi.GetProperty("h").GetDouble(),
        };
    }
}

public sealed class Roi
{
    public double X { get; set; }
    public double Y { get; set; }
    public double W { get; set; }
    public double H { get; set; }
}
