using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using QuizAnswerTool.Core;
using RapidOcrNet;

var modelDir = @"D:\work\mhxy\quiz-answer-tool-cs\VerifyOcr\bin\Debug\net8.0-windows10.0.19041.0\models";
var bank = QuestionBank.Load(@"D:\work\mhxy\quiz-answer-tool\questions.json");
var cfg = Config.Load(@"D:\work\mhxy\quiz-answer-tool\config.json");
var files = Directory.GetFiles(@"C:\Users\admin\Downloads", "screenshot-20260809-*.png").OrderBy(f => f).ToList();
var qTmp = @"C:\Users\admin\AppData\Local\Temp\opencode\q_tmp.png";
var oTmp = @"C:\Users\admin\AppData\Local\Temp\opencode\o_tmp.png";

var models = new (string Name, string Det, string Rec)[]
{
    ("v6-small", $@"{modelDir}\v6\PP-OCRv6_det_small.onnx", $@"{modelDir}\v6\PP-OCRv6_rec_small.onnx"),
    ("v6-medium", $@"{modelDir}\v6\PP-OCRv6_det_medium.onnx", $@"{modelDir}\v6\PP-OCRv6_rec_medium.onnx"),
};

foreach (var m in models)
{
    using var ocr = new RapidOcr();
    ocr.InitModels(m.Det, $@"{modelDir}\v6\cls.onnx", m.Rec, $@"{modelDir}\v6\ppocrv6_dict.txt", numThread: 4);
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
        qBmp.Save(qTmp);
        sw.Restart();
        var qRes = ocr.Detect(qTmp, RapidOcrOptions.PPOCRv6);
        sw.Stop();
        tq.Add(sw.Elapsed.TotalMilliseconds);
        string qText = string.Join("", qRes.TextBlocks.Select(b => b.Text));
        var q = bank.Match(qText);
        if (q != null)
        {
            okQ++;
            var answer = q.GetValueOrDefault("answer")?.ToString() ?? "";
            using var oBmp = full.Clone(oRect, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
            oBmp.Save(oTmp);
            var oRes = ocr.Detect(oTmp, RapidOcrOptions.PPOCRv6);
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
    Console.WriteLine($"{m.Name}: 题目 {okQ}/{files.Count}, 答案 {okA}/{okQ}, 题目OCR均 {tq.Average():F0}ms");
    foreach (var ms in misses) Console.WriteLine("  MISS " + ms);
    Console.WriteLine();
}
