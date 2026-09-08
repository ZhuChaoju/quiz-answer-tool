using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using QuizAnswerTool.Core;
using RapidOcrNet;
using SkiaSharp;

var root = @"D:\work\quiz-answer-tool-csharp";
var modelDir = $@"{root}\QuizAnswerTool\models";
var bank = QuestionBank.Load($@"{root}\questions.json");
var cfg = Config.Load($@"{root}\config.json");
// 图片目录可用命令行参数指定（默认合成科举题图；真实活动截图传 Downloads\截图）
var shotDir = args.Length > 0 ? args[0] : @"D:\work\_downloads\shots";
var files = Directory.GetFiles(shotDir, "*.png").OrderBy(f => f).ToList();
Console.WriteLine($"模型目录: {modelDir}");
Console.WriteLine($"截图: {files.Count} 张 来自 {shotDir}");

// 模型档位：tiny 用独立字典 ppocrv6_tiny_dict.txt，small/medium 用 ppocrv6_dict.txt
// 可用第二参数只跑一档（独立进程、退出即释放，避免多引擎并存导致资源峰值）
var tier = args.Length > 1 ? args[1] : "";
var allModels = new (string Name, string Det, string Rec, string Keys)[]
{
    ("v6-tiny",   $@"{modelDir}\v6\PP-OCRv6_det_tiny.onnx",   $@"{modelDir}\v6\PP-OCRv6_rec_tiny.onnx",   $@"{modelDir}\v6\ppocrv6_tiny_dict.txt"),
    ("v6-small",  $@"{modelDir}\v6\PP-OCRv6_det_small.onnx",  $@"{modelDir}\v6\PP-OCRv6_rec_small.onnx",  $@"{modelDir}\v6\ppocrv6_dict.txt"),
    ("v6-medium", $@"{modelDir}\v6\PP-OCRv6_det_medium.onnx", $@"{modelDir}\v6\PP-OCRv6_rec_medium.onnx", $@"{modelDir}\v6\ppocrv6_dict.txt"),
};
var models = allModels.Where(m => tier == "" || m.Name == $"v6-{tier}").ToArray();

foreach (var m in models)
{
    if (!File.Exists(m.Det) || !File.Exists(m.Rec) || !File.Exists(m.Keys))
    {
        Console.WriteLine($"{m.Name}: 模型文件缺失，跳过（{m.Det}）");
        continue;
    }
    using var ocr = new RapidOcr();
    ocr.InitModels(m.Det, $@"{modelDir}\v6\cls.onnx", m.Rec, m.Keys, numThread: 4);
    int okQ = 0, okA = 0;
    var tq = new List<double>();
    var sw = new Stopwatch();
    var misses = new List<string>();
    foreach (var f in files)
    {
        using var full = new Bitmap(f);
        var rect = new Rectangle(0, 0, full.Width, full.Height);
        var qRect = ScreenCapture.CropRegion(rect, cfg.QuestionRoi.X, cfg.QuestionRoi.Y, cfg.QuestionRoi.W, cfg.QuestionRoi.H);
        var oRect = ScreenCapture.CropRegion(rect, cfg.OptionRoi.X, cfg.OptionRoi.Y, cfg.OptionRoi.W, cfg.OptionRoi.H);
        string name = Path.GetFileName(f);
        using var qBmp = full.Clone(qRect, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
        sw.Restart();
        using (var qSk = ToSkBitmap(qBmp))
        {
            // 纯内存识别（旧版经 PNG 落盘往返，此处计时不含那次开销）
            var qRes = ocr.Detect(qSk, RapidOcrOptions.PPOCRv6);
            sw.Stop();
            tq.Add(sw.Elapsed.TotalMilliseconds);
            string qText = string.Join("", qRes.TextBlocks.Select(b => b.Text));
            var q = bank.Match(qText);
            if (q != null)
            {
                okQ++;
                var answer = q.GetValueOrDefault("answer")?.ToString() ?? "";
                using var oBmp = full.Clone(oRect, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
                using var oSk = ToSkBitmap(oBmp);
                var oRes = ocr.Detect(oSk, RapidOcrOptions.PPOCRv6);
                var oLines = oRes.TextBlocks.Select(b => new OcrLine
                {
                    Text = b.Text,
                    CenterX = b.BoxPoints.Average(p => p.X),
                    CenterY = b.BoxPoints.Average(p => p.Y),
                    Width = Math.Abs(b.BoxPoints[0].X - b.BoxPoints[2].X),
                    Height = Math.Abs(b.BoxPoints[0].Y - b.BoxPoints[2].Y),
                }).ToList();
                if (AnswerLocator.Find(oLines, answer) != null) okA++;
            }
            else misses.Add($"{name}: {qText[..Math.Min(qText.Length, 50)]}");
        }
    }
    Console.WriteLine($"{m.Name}: 题目 {okQ}/{files.Count}, 答案 {okA}/{okQ}, 题目OCR均 {tq.Average():F0}ms");
    foreach (var ms in misses) Console.WriteLine("  MISS " + ms);
    Console.WriteLine();
}

/// <summary>System.Drawing.Bitmap → SKBitmap（Format32bppArgb 内存布局即 BGRA，整块拷贝）。</summary>
static SKBitmap ToSkBitmap(Bitmap bmp)
{
    var sk = new SKBitmap(bmp.Width, bmp.Height, SKColorType.Bgra8888, SKAlphaType.Unpremul);
    var bd = bmp.LockBits(new Rectangle(0, 0, bmp.Width, bmp.Height),
        System.Drawing.Imaging.ImageLockMode.ReadOnly, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
    try
    {
        var buffer = new byte[bd.Stride * bmp.Height];
        Marshal.Copy(bd.Scan0, buffer, 0, buffer.Length);
        Marshal.Copy(buffer, 0, sk.GetPixels(), buffer.Length);
    }
    finally { bmp.UnlockBits(bd); }
    return sk;
}
