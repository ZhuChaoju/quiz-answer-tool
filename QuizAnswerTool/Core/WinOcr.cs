using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using Microsoft.ML.OnnxRuntime;
using RapidOcrNet;
using SkiaSharp;

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

/// <summary>RapidOcrNet 引擎封装：PP-OCRv6 模型（默认 tiny），纯内存识别，可选 DirectML GPU。</summary>
public static class WinOcr
{
    private static RapidOcr? _engine;
    private static RapidOcr? _engine2;  // 第二个引擎实例：题目/选项并行识别
    private static readonly object _lock = new();

    public static void EnsureEngine(string modelDir, string modelType = "tiny", bool useDml = false)
    {
        if (_engine != null) return;
        lock (_lock)
        {
            if (_engine != null) return;
            // 模型集候选：配置优先，缺文件时按 tiny→small→medium 回退（tiny 用独立字典）
            var candidates = new (string Type, string Det, string Rec, string Keys)[]
            {
                ("tiny",   "PP-OCRv6_det_tiny.onnx",   "PP-OCRv6_rec_tiny.onnx",   "ppocrv6_tiny_dict.txt"),
                ("small",  "PP-OCRv6_det_small.onnx",  "PP-OCRv6_rec_small.onnx",  "ppocrv6_dict.txt"),
                ("medium", "PP-OCRv6_det_medium.onnx", "PP-OCRv6_rec_medium.onnx", "ppocrv6_dict.txt"),
            };
            var ordered = candidates.Where(c => c.Type == modelType)
                .Concat(candidates.Where(c => c.Type != modelType));
            string? det = null, rec = null, keys = null;
            foreach (var c in ordered)
            {
                det = FindModel(modelDir, "v6", c.Det);
                rec = FindModel(modelDir, "v6", c.Rec);
                keys = FindModel(modelDir, "v6", c.Keys);
                if (det != null && rec != null && keys != null) break;
            }
            if (det == null || rec == null || keys == null)
                throw new InvalidOperationException(
                    "RapidOCR v6 模型缺失，请将 det/rec onnx 与字典放到程序目录 models/v6/"
                    + "（tiny 需要 ppocrv6_tiny_dict.txt，small/medium 用 ppocrv6_dict.txt）");
            var cls = FindModel(modelDir, "v6", "cls.onnx") ?? "";

            // 主引擎留 2 核给系统/预览/第二引擎；use_dml 需引用 Microsoft.ML.OnnxRuntime.DirectML 包
            int mainThreads = Math.Max(2, Environment.ProcessorCount - 2);
            var ocr = new RapidOcr();
            InitEngine(ocr, det, cls, rec, keys, useDml, mainThreads);
            _engine = ocr;
            var ocr2 = new RapidOcr();
            InitEngine(ocr2, det, cls, rec, keys, useDml, 2);
            _engine2 = ocr2;
        }
    }

    private static void InitEngine(RapidOcr ocr, string det, string cls, string rec, string keys, bool useDml, int numThread)
    {
        if (useDml)
        {
            using var op = new SessionOptions();
            op.AppendExecutionProvider_DML();
            ocr.InitModels(det, cls, rec, keys, op);
        }
        else
        {
            ocr.InitModels(det, cls, rec, keys, numThread);
        }
    }

    private static string? FindModel(string baseDir, string sub, string name)
    {
        foreach (var root in new[] { baseDir, Path.Combine(baseDir, "models"), Path.Combine(AppContext.BaseDirectory, "models") })
        {
            var p = Path.Combine(root, sub, name);
            if (File.Exists(p)) return p;
        }
        return null;
    }

    /// <summary>识别 Bitmap（纯内存，不再经临时 PNG 落盘）。</summary>
    public static List<OcrLine> Recognize(Bitmap bmp)
        => RecognizeInternal(bmp, _engine ?? throw new InvalidOperationException("引擎未初始化"));

    /// <summary>用第二引擎识别（与 Recognize 可并行调用）。</summary>
    public static List<OcrLine> RecognizeParallel(Bitmap bmp)
        => RecognizeInternal(bmp, _engine2 ?? _engine ?? throw new InvalidOperationException("引擎未初始化"));

    private static List<OcrLine> RecognizeInternal(Bitmap bmp, RapidOcr engine)
    {
        using var src = ToSkBitmap(bmp);
        var result = engine.Detect(src, RapidOcrOptions.PPOCRv6);
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

    /// <summary>System.Drawing.Bitmap → SKBitmap：Format32bppArgb 内存布局即 BGRA，与 Bgra8888/Unpremul
    /// 逐字节一致，整块拷贝（替代原 PNG 编码落盘+重新解码的往返）。</summary>
    private static SKBitmap ToSkBitmap(Bitmap bmp)
    {
        var sk = new SKBitmap(bmp.Width, bmp.Height, SKColorType.Bgra8888, SKAlphaType.Unpremul);
        var bd = bmp.LockBits(new Rectangle(0, 0, bmp.Width, bmp.Height),
            ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try
        {
            var buffer = new byte[bd.Stride * bmp.Height];
            Marshal.Copy(bd.Scan0, buffer, 0, buffer.Length);
            Marshal.Copy(buffer, 0, sk.GetPixels(), buffer.Length);
        }
        finally { bmp.UnlockBits(bd); }
        return sk;
    }
}
