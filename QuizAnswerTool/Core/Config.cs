using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace QuizAnswerTool.Core;

/// <summary>配置文件（兼容原 config.json 格式，新增 question_roi/option_roi 写死区域）。</summary>
public sealed class Config
{
    public double IntervalSec { get; set; } = 0.2;
    public Roi QuestionRoi { get; set; } = new() { X = 28.0, Y = 23.0, W = 55.0, H = 24.0 };
    public Roi OptionRoi { get; set; } = new() { X = 25.0, Y = 44.0, W = 70.0, H = 24.0 };
    public double Confidence { get; set; } = 0.4;

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
            if (root.TryGetProperty("ocr", out var ocr) && ocr.TryGetProperty("confidence", out var oc))
                cfg.Confidence = oc.GetDouble();
            cfg.QuestionRoi = ParseRoi(root, "question_roi") ?? cfg.QuestionRoi;
            cfg.OptionRoi = ParseRoi(root, "option_roi") ?? cfg.OptionRoi;
        }
        catch { /* 配置损坏时用默认 */ }
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
