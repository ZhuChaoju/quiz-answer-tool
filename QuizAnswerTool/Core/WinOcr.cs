using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using RapidOcrNet;

namespace QuizAnswerTool.Core;

/// <summary>一行识别结果（坐标基于输入图片像素）。</summary>
public sealed class OcrLine
{
    public string Text { get; init; } = "";
    public double CenterX { get; init; }
    public double CenterY { get; init; }
    public double Width { get; init; }
    public double Height { get; init; }
    /// <summary>行内各段文本与水平占比 (left, right)。</summary>
    public List<(string Text, double Left, double Right)> Segments { get; init; } = new();
}

/// <summary>RapidOcrNet 引擎封装：PP-OCRv6 small 多语言模型，中文识别精准、CPU 可控。</summary>
public static class WinOcr
{
    private static RapidOcr? _engine;
    private static RapidOcr? _engine2;  // 第二个引擎实例：题目/选项并行识别
    private static readonly object _lock = new();

    public static void EnsureEngine(string modelDir)
    {
        if (_engine != null) return;
        lock (_lock)
        {
            if (_engine != null) return;
            var det = FindModel(modelDir, "v6", "PP-OCRv6_det_small.onnx");
            var cls = FindModel(modelDir, "v6", "cls.onnx");
            var rec = FindModel(modelDir, "v6", "PP-OCRv6_rec_small.onnx");
            var keys = FindModel(modelDir, "v6", "ppocrv6_dict.txt");
            if (det == null || rec == null || keys == null)
                throw new InvalidOperationException("RapidOCR v6 模型缺失，请将模型文件放到程序目录 models/v6/");
            var ocr = new RapidOcr();
            ocr.InitModels(det, cls ?? "", rec, keys, numThread: 4);
            _engine = ocr;
            var ocr2 = new RapidOcr();
            ocr2.InitModels(det, cls ?? "", rec, keys, numThread: 2);
            _engine2 = ocr2;
        }
    }

    private static string? FindModel(string baseDir, string sub, string name)
    {
        foreach (var root in new[] { baseDir, Path.Combine(baseDir, "models"), Path.Combine(Path.GetDirectoryName(Environment.ProcessPath) ?? "", "models") })
        {
            var p = Path.Combine(root, sub, name);
            if (File.Exists(p)) return p;
        }
        return null;
    }

    public static List<OcrLine> Recognize(string imagePath, double minConfidence = 0.0)
        => RecognizeInternal(imagePath, _engine ?? throw new InvalidOperationException("引擎未初始化"));

    /// <summary>用第二引擎识别（与 Recognize 可并行调用）。</summary>
    public static List<OcrLine> RecognizeParallel(string imagePath, double minConfidence = 0.0)
        => RecognizeInternal(imagePath, _engine2 ?? _engine ?? throw new InvalidOperationException("引擎未初始化"));

    private static List<OcrLine> RecognizeInternal(string imagePath, RapidOcr engine)
    {
        var result = engine.Detect(imagePath, RapidOcrOptions.PPOCRv6);
        var lines = new List<OcrLine>();
        foreach (var block in result.TextBlocks)
        {
            if (string.IsNullOrWhiteSpace(block.Text)) continue;
            var pts = block.BoxPoints;
            double minX = pts.Min(p => p.X), maxX = pts.Max(p => p.X);
            double minY = pts.Min(p => p.Y), maxY = pts.Max(p => p.Y);
            double w = maxX - minX, h = maxY - minY;
            if (w <= 0 || h <= 0) continue;
            lines.Add(new OcrLine
            {
                Text = block.Text,
                CenterX = (minX + maxX) / 2,
                CenterY = (minY + maxY) / 2,
                Width = w,
                Height = h,
                Segments = new List<(string, double, double)> { (block.Text, 0.0, 1.0) },
            });
        }
        lines.Sort((a, b) => a.CenterY.CompareTo(b.CenterY));
        return lines;
    }

    /// <summary>Bitmap 重载：保存临时文件后识别。</summary>
    public static List<OcrLine> Recognize(Bitmap bmp, string tmpDir, double minConfidence = 0.0)
        => RecognizeFile(bmp, tmpDir, "ocr_tmp.png", parallel: false, minConfidence);

    /// <summary>Bitmap 并行重载：题目/选项可同时识别。</summary>
    public static List<OcrLine> RecognizeParallel(Bitmap bmp, string tmpDir, double minConfidence = 0.0)
        => RecognizeFile(bmp, tmpDir, "ocr_tmp_p.png", parallel: true, minConfidence);

    private static List<OcrLine> RecognizeFile(Bitmap bmp, string tmpDir, string name, bool parallel, double minConfidence)
    {
        var tmp = Path.Combine(tmpDir, name);
        bmp.Save(tmp, ImageFormat.Png);
        return parallel ? RecognizeParallel(tmp, minConfidence) : Recognize(tmp, minConfidence);
    }
}
