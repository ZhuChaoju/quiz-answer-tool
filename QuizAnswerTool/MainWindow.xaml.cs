using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using QuizAnswerTool.Core;
using WpfCanvas = System.Windows.Controls.Canvas;
using PixelFormat = System.Drawing.Imaging.PixelFormat;

namespace QuizAnswerTool;

public partial class MainWindow : Window
{
    private static readonly System.Windows.Media.Color AnswerColor = System.Windows.Media.Color.FromRgb(0xff, 0x40, 0x40);
    private static readonly System.Windows.Media.Color QuestionZoneColor = System.Windows.Media.Color.FromRgb(0x00, 0xff, 0x00);
    private static readonly System.Windows.Media.Color OptionZoneColor = System.Windows.Media.Color.FromRgb(0x00, 0xaa, 0xff);

    private readonly Config _cfg;
    private QuestionBank? _bank;
    private IconBank _icons = new();
    private string _iconsPath = "icons.json";
    private string _lastIconHash = "";
    private string _activity = "keju";   // keju=科举文字题 / picture=看图说话
    private List<ScreenSource> _sources = new();
    private CancellationTokenSource? _cts;
    private string _lastQuestion = "";
    private string _questionsPath = "questions.json";
    private double _previewScale = 1.0;
    private (double X, double Y) _previewOffset;
    private (double W, double H) _previewDispSize;
    private System.Drawing.Size _fullSize;
    private string _tmpDir = "";
    // 识别实际使用的 ROI（UI 可拖拽实时更新；后台线程按引用快照读取）
    private Roi _qRoi = new();   // 科举=题目区 / 看图说话=图标区
    private Roi _oRoi = new();   // 选项区（按活动独立）
    private (Roi Q, Roi O) _kejuRois;
    private (Roi Q, Roi O) _pictureRois;
    private bool _dragging;
    private string _dragTarget = "q";    // 拖的是题目框(q)还是选项框(o)
    private string _dragMode = "move";   // move / resize / create
    private (double X, double Y) _dragStart;   // 按下时图内坐标
    private System.Drawing.Rectangle _dragOrig;  // 按下时框的图内像素矩形

    // 预览元素常驻复用：每帧只更新像素与坐标，不重建子元素
    private const int PreviewFps = 30;
    private System.Windows.Controls.Image? _previewImage;
    private System.Windows.Shapes.Rectangle? _qZoneRect;
    private System.Windows.Shapes.Rectangle? _oZoneRect;
    private System.Windows.Shapes.Rectangle? _answerRect;
    private WriteableBitmap? _previewBitmap;

    public MainWindow()
    {
        InitializeComponent();
        ScreenCapture.EnableDpiAware();

        // 数据文件：exe 所在目录 → 工作目录 → exe 上级目录（源码运行时）→ 项目根
        // AppContext.BaseDirectory：`dotnet <app>.dll` 启动时 Environment.ProcessPath 指向 dotnet.exe，
        // 会把模型/数据文件定位到 SDK 目录；BaseDirectory 始终指向应用自身目录
        var baseDir = AppContext.BaseDirectory;
        var candidates = new List<string> { baseDir, Directory.GetCurrentDirectory() };
        var parent = Directory.GetParent(baseDir)?.FullName;
        while (parent != null && candidates.Count < 8)
        {
            candidates.Add(parent);
            parent = Directory.GetParent(parent)?.FullName;
        }
        var configPath = candidates.Select(d => Path.Combine(d, "config.json")).FirstOrDefault(File.Exists) ?? "config.json";
        var questionsPath = candidates.Select(d => Path.Combine(d, "questions.json")).FirstOrDefault(File.Exists) ?? "questions.json";

        _tmpDir = Path.Combine(Path.GetTempPath(), "quiz_answer_tool");
        Directory.CreateDirectory(_tmpDir);

        _cfg = Config.Load(configPath);
        _questionsPath = questionsPath;
        _kejuRois = (new Roi { X = _cfg.QuestionRoi.X, Y = _cfg.QuestionRoi.Y, W = _cfg.QuestionRoi.W, H = _cfg.QuestionRoi.H },
                     new Roi { X = _cfg.OptionRoi.X, Y = _cfg.OptionRoi.Y, W = _cfg.OptionRoi.W, H = _cfg.OptionRoi.H });
        _pictureRois = (new Roi { X = _cfg.PictureIconRoi.X, Y = _cfg.PictureIconRoi.Y, W = _cfg.PictureIconRoi.W, H = _cfg.PictureIconRoi.H },
                        new Roi { X = _cfg.PictureOptionRoi.X, Y = _cfg.PictureOptionRoi.Y, W = _cfg.PictureOptionRoi.W, H = _cfg.PictureOptionRoi.H });
        _activity = _cfg.Activity;
        (_qRoi, _oRoi) = _activity == "picture" ? _pictureRois : _kejuRois;
        try { _bank = QuestionBank.Load(questionsPath); StatusText.Text = $"题库已加载 {_bank.Count} 题"; }
        catch (Exception ex) { StatusText.Text = $"题库加载失败: {ex.Message}"; }
        // 图标库与数据文件同目录查找（与 questions.json 相同的候选链）；
        // 尚不存在时锚定 exe 目录，避免相对路径随进程 CWD 漂移、下次启动找不到
        var iconsPath = candidates.Select(d => Path.Combine(d, "icons.json")).FirstOrDefault(File.Exists)
                        ?? Path.Combine(baseDir, "icons.json");
        _iconsPath = iconsPath;
        _icons = IconBank.Load(iconsPath);
        try { WinOcr.EnsureEngine(baseDir, _cfg.ModelType, _cfg.UseDml); }
        catch (Exception ex) { StatusText.Text = $"OCR引擎初始化失败: {ex.Message}"; }

        ActivityBox.Items.Add("科举文字题");
        ActivityBox.Items.Add("看图说话");
        ActivityBox.SelectedIndex = _activity == "picture" ? 1 : 0;
        UpdateRoiLabel();

        RefreshSources();
        // 贴屏幕右缘
        Left = SystemParameters.WorkArea.Right - Width - 10;
        Top = (SystemParameters.WorkArea.Height - Height) / 2;
    }

    private void OnLoaded(object sender, RoutedEventArgs e) { }

    /// <summary>活动切换：科举(题库文字匹配) / 看图说话(图标哈希匹配)，ROI 跟随切换。</summary>
    private void OnActivityChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
    {
        if (ActivityBox.SelectedIndex < 0) return;
        _activity = ActivityBox.SelectedIndex == 1 ? "picture" : "keju";
        (_qRoi, _oRoi) = _activity == "picture" ? _pictureRois : _kejuRois;
        _lastIconHash = "";
        DrawZones();
        UpdateRoiLabel();
    }

    private void RefreshSources()
    {
        _sources = ScreenCapture.ListSources();
        SourceBox.ItemsSource = _sources.Select(s => s.Name).ToList();
        if (_sources.Count > 0)
        {
            // 配置了窗口关键词时自动选中匹配窗口，否则取第一个窗口源
            string kw = _cfg.WindowKeyword;
            int idx = kw.Length > 0
                ? _sources.FindIndex(s => s.Kind == "window" && s.Name.Contains(kw))
                : _sources.FindIndex(s => s.Kind == "window");
            SourceBox.SelectedIndex = idx >= 0 ? idx : 0;
        }
    }

    private void OnRefreshSources(object sender, RoutedEventArgs e) => RefreshSources();

    private void OnToggle(object sender, RoutedEventArgs e)
    {
        if (_cts != null)
        {
            _cts.Cancel();
            _cts = null;
            StartBtn.Content = "开始";
            StatusText.Text = "已停止";
            return;
        }
        if (SourceBox.SelectedIndex < 0) return;
        var source = _sources[SourceBox.SelectedIndex];
        _cts = new CancellationTokenSource();
        StartBtn.Content = "停止";
        StatusText.Text = "运行中…";
        var token = _cts.Token;
        _ = Task.Run(() => PreviewLoop(source, token));
        _ = Task.Run(() => RecognitionLoop(source, token));
    }

    private void RecognitionLoop(ScreenSource source, CancellationToken ct)
    {
        var log = Path.Combine(_tmpDir, "debug.log");
        void Log(string msg) { try { File.AppendAllText(log, $"{DateTime.Now:HH:mm:ss.fff} {msg}\n"); } catch { } }
        Log($"识别循环启动, source={source.Name}, activity={_activity}");
        string? lastKey = null;
        string? lastHash = null;
        while (!ct.IsCancellationRequested)
        {
            Thread.Sleep((int)(_cfg.IntervalSec * 1000));
            try
            {
                var (full, rect) = ScreenCapture.Capture(source);
                using (full)
                {
                    _fullSize = full.Size;
                    // ROI 取 UI 当前值：预览里拖拽题目/选项框立即对识别生效（后台线程按快照读取）
                    var qRoi = _qRoi;
                    var oRoi = _oRoi;
                    var qRect = ScreenCapture.CropRegion(rect, qRoi.X, qRoi.Y, qRoi.W, qRoi.H);
                    var oRect = ScreenCapture.CropRegion(rect, oRoi.X, oRoi.Y, oRoi.W, oRoi.H);

                    using (var qBmp = Crop(full, qRect))
                    using (var oBmp = Crop(full, oRect))
                    {
                        // 感知哈希闸门：题目/图标区画面未变则整轮跳过（毫秒级，替代原每轮无条件 OCR）
                        string hash = ComputeHash(qBmp);
                        if (hash == lastHash) { continue; }
                        lastHash = hash;

                        if (_activity == "picture")
                        {
                            // 看图说话：图标哈希定答案，选项区 OCR 仅用于红框定位
                            _lastIconHash = IconBank.HashIcon(qBmp);
                            string? iconAnswer = _icons.Match(_lastIconHash);
                            var oLines0 = WinOcr.Recognize(oBmp).Where(ln => !IsUiNoise(ln.Text)).ToList();
                            string display = iconAnswer != null
                                ? $"看图识别: {iconAnswer}"
                                : "看图识别: 图标未收录,请在下方录入答案";
                            var hit0 = iconAnswer != null ? AnswerLocator.Find(oLines0, iconAnswer) : null;
                            if (hit0 != null)
                            {
                                var l0 = hit0.Value.Line;
                                Dispatcher.Invoke(() => DrawAnswerBox(
                                    oRect.Left + l0.CenterX, oRect.Top + l0.CenterY,
                                    l0.Width, l0.Height, hit0.Value.Left, hit0.Value.Right, rect));
                            }
                            Dispatcher.Invoke(() =>
                            {
                                _lastQuestion = display;
                                QuestionText.Text = "题目: " + display;
                                AnswerText.Text = iconAnswer != null ? "答案: " + iconAnswer : "未收录";
                                RawText.Text = "识别文本: " + display + "\n" +
                                               string.Join("\n", oLines0.Select(ln => ln.Text));
                                if (hit0 == null && _answerRect != null)
                                    _answerRect.Visibility = Visibility.Collapsed;
                            });
                            Log($"看图: {iconAnswer ?? "未收录"} hash={_lastIconHash}");
                            continue;
                        }

                        // 题目/选项双引擎并行识别（原为串行等待）
                        var qTask = Task.Run(() => WinOcr.Recognize(qBmp));
                        var oTask = Task.Run(() => WinOcr.RecognizeParallel(oBmp));
                        var qLines = qTask.GetAwaiter().GetResult().Where(ln => !IsUiNoise(ln.Text)).ToList();
                        var oLines = oTask.GetAwaiter().GetResult().Where(ln => !IsUiNoise(ln.Text)).ToList();
                        if (qLines.Count == 0) { continue; }
                        qLines.Sort((a, b) => a.CenterY.CompareTo(b.CenterY));
                        string qText = string.Join("", qLines.Select(ln => ln.Text));
                        // 非答题场景：识别到的都是玩家名等噪声，内容极短则跳过（题目至少 5 字）
                        if (qText.Length < 5) { continue; }
                        var key = string.Join("|", qLines.Take(2).Select(ln => ln.Text));
                        if (key == lastKey) { continue; }
                        lastKey = key;
                        Log($"题目: {qText}");

                        var question = _bank?.Match(qText);
                        Log($"匹配: {(question != null ? question.GetValueOrDefault("answer") : "null")}");
                        string answer = question?.GetValueOrDefault("answer")?.ToString() ?? "";
                        string qDisplay = question?.GetValueOrDefault("question")?.ToString() ?? qText;

                        OcrLine? answerLine = null;
                        double left = 0, right = 1;
                        if (!string.IsNullOrEmpty(answer))
                        {
                            var hit = AnswerLocator.Find(oLines, answer);
                            if (hit != null)
                            {
                                answerLine = hit.Value.Line;
                                left = hit.Value.Left;
                                right = hit.Value.Right;
                                double ox = oRect.Left + answerLine.CenterX;
                                double oy = oRect.Top + answerLine.CenterY;
                                Dispatcher.Invoke(() => DrawAnswerBox(ox, oy, answerLine.Width, answerLine.Height, left, right, rect));
                            }
                        }
                        Dispatcher.Invoke(() =>
                        {
                            _lastQuestion = qDisplay;
                            QuestionText.Text = "题目: " + qDisplay;
                            AnswerText.Text = string.IsNullOrEmpty(answer) ? "未命中" : "答案: " + answer;
                            RawText.Text = "识别文本: " + string.Join("\n", qLines.Select(ln => ln.Text)) + "\n" +
                                           string.Join("\n", oLines.Select(ln => ln.Text));
                            // 未命中时隐藏旧答案框（元素常驻，不再靠整幅重绘清除）
                            if (answerLine == null && _answerRect != null)
                                _answerRect.Visibility = Visibility.Collapsed;
                        });
                    }
                }
            }
            catch (OperationCanceledException) { break; }
            catch (Exception ex)
            {
                Log($"错误: {ex.Message}");
                Dispatcher.Invoke(() => AnswerText.Text = "识别错误: " + ex.Message);
            }
        }
    }

    /// <summary>轻量画面校验：LockBits 采样，毫秒级。</summary>
    private static unsafe ulong PixelStamp(System.Drawing.Bitmap bmp)
    {
        ulong v = 0;
        var data = bmp.LockBits(new Rectangle(0, 0, bmp.Width, bmp.Height),
            System.Drawing.Imaging.ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try
        {
            int stride = data.Stride;
            int stepX = Math.Max(bmp.Width / 10, 1);
            int stepY = Math.Max(bmp.Height / 6, 1);
            byte* basePtr = (byte*)data.Scan0;
            for (int y = 0; y < bmp.Height; y += stepY)
                for (int x = 0; x < bmp.Width; x += stepX)
                {
                    byte* p = basePtr + y * stride + x * 4;
                    v = v * 131 + (uint)((p[2] >> 4) * 31 + (p[1] >> 4) * 7 + (p[0] >> 4));
                }
        }
        finally { bmp.UnlockBits(data); }
        return v;
    }

    private void OnEntryKey(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter) AddAnswer();
    }

    private void OnAddAnswer(object sender, RoutedEventArgs e) => AddAnswer();

    private void AddAnswer()
    {
        var text = EntryBox.Text.Trim();
        if (string.IsNullOrEmpty(text)) return;
        if (_activity == "picture" && _lastIconHash.Length > 0)
        {
            // 看图说话：答案连同当前图标哈希写入 icons.json
            _icons.Add(_lastIconHash, text);
            try { _icons.Save(_iconsPath); }
            catch (Exception ex) { AnswerText.Text = "写入图标库失败: " + ex.Message; return; }
            AnswerText.Text = $"已收录图标: {text}（共 {_icons.Count} 个）";
            EntryBox.Text = "";
            return;
        }
        if (string.IsNullOrEmpty(_lastQuestion) || _bank == null) return;
        _bank.Add(_lastQuestion, text);
        SaveBankToFile(text);
        AnswerText.Text = $"已收录: {_lastQuestion} → {text}";
        EntryBox.Text = "";
    }

    // ---- ROI 拖拽（题目/图标框绿 + 选项框蓝；框内拖动、右下角缩放、空白处拖出新题目框） ----

    private (double X, double Y) CanvasToImagePercent(System.Windows.Point p)
    {
        double fx = (p.X - _previewOffset.X) / _previewScale;
        double fy = (p.Y - _previewOffset.Y) / _previewScale;
        return (_fullSize.Width > 0 ? fx / _fullSize.Width * 100 : 0,
                _fullSize.Height > 0 ? fy / _fullSize.Height * 100 : 0);
    }

    private void OnCanvasDown(object sender, MouseButtonEventArgs e)
    {
        if (_fullSize.Width == 0 || _fullSize.Height == 0) return;
        var (px, py) = CanvasToImagePercent(e.GetPosition(PreviewCanvas));
        // 命中哪个框拖哪个（选项框判定在前：两框相邻时优先响应更小的选项框）
        foreach (var (target, roi) in new[] { ("o", _oRoi), ("q", _qRoi) })
        {
            if (px >= roi.X && px <= roi.X + roi.W && py >= roi.Y && py <= roi.Y + roi.H)
            {
                // 右下角 14 画布像素 = 缩放手柄
                double handleW = _fullSize.Width > 0 ? 14.0 / _previewScale / _fullSize.Width * 100 : 2;
                double handleH = _fullSize.Height > 0 ? 14.0 / _previewScale / _fullSize.Height * 100 : 2;
                _dragTarget = target;
                _dragMode = px > roi.X + roi.W - handleW && py > roi.Y + roi.H - handleH ? "resize" : "move";
                _dragStart = (px, py);
                _dragOrig = new System.Drawing.Rectangle((int)roi.X, (int)roi.Y, (int)roi.W, (int)roi.H);
                _dragging = true;
                PreviewCanvas.CaptureMouse();
                return;
            }
        }
        _dragTarget = "q";
        _dragMode = "create";
        _dragStart = (px, py);
        _dragOrig = new System.Drawing.Rectangle();
        _dragging = true;
        PreviewCanvas.CaptureMouse();
    }

    private void OnCanvasMove(object sender, MouseEventArgs e)
    {
        if (!_dragging) return;
        var (px, py) = CanvasToImagePercent(e.GetPosition(PreviewCanvas));
        double ox = _dragOrig.X, oy = _dragOrig.Y, ow = _dragOrig.Width, oh = _dragOrig.Height;
        var (sx, sy) = _dragStart;
        double nx, ny, nw, nh;
        if (_dragMode == "move") { nx = ox + px - sx; ny = oy + py - sy; nw = ow; nh = oh; }
        else if (_dragMode == "resize") { nx = ox; ny = oy; nw = px - ox; nh = py - oy; }
        else { nx = Math.Min(sx, px); ny = Math.Min(sy, py); nw = Math.Abs(px - sx); nh = Math.Abs(py - sy); }
        nx = Math.Max(0, Math.Min(nx, 99));
        ny = Math.Max(0, Math.Min(ny, 99));
        nw = Math.Max(1, Math.Min(nw, 100 - nx));
        nh = Math.Max(1, Math.Min(nh, 100 - ny));
        var roi = new Roi { X = nx, Y = ny, W = nw, H = nh };
        if (_dragTarget == "o") _oRoi = roi; else _qRoi = roi;
        DrawZones();
        UpdateRoiLabel();
    }

    private void OnCanvasUp(object sender, MouseButtonEventArgs e)
    {
        if (!_dragging) return;
        _dragging = false;
        PreviewCanvas.ReleaseMouseCapture();
    }

    private void UpdateRoiLabel()
    {
        string first = _activity == "picture" ? "图标ROI" : "题目ROI";
        RoiText.Text = $"{first}: x={_qRoi.X:F1}% y={_qRoi.Y:F1}% w={_qRoi.W:F1}% h={_qRoi.H:F1}%  " +
                       $"选项ROI: x={_oRoi.X:F1}% y={_oRoi.Y:F1}% w={_oRoi.W:F1}% h={_oRoi.H:F1}%";
    }

    /// <summary>把录入的答案写回 questions.json（同题覆盖 answer，否则追加）。</summary>
    private void SaveBankToFile(string text)
    {
        try
        {
            var json = File.ReadAllText(_questionsPath, Encoding.UTF8);
            var items = JsonSerializer.Deserialize<List<Dictionary<string, object?>>>(json)
                        ?? new List<Dictionary<string, object?>>();
            var hit = items.FirstOrDefault(i => i.GetValueOrDefault("question")?.ToString() == _lastQuestion);
            if (hit != null)
            {
                hit["answer"] = text;
            }
            else
            {
                items.Add(new Dictionary<string, object?>
                {
                    ["id"] = items.Count + 1,
                    ["question"] = _lastQuestion,
                    ["options"] = new List<object?>(),
                    ["answer"] = text,
                });
            }
            File.WriteAllText(
                _questionsPath,
                JsonSerializer.Serialize(items, new JsonSerializerOptions
                {
                    WriteIndented = true,
                    Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
                }),
                Encoding.UTF8);
        }
        catch (Exception ex)
        {
            AnswerText.Text = "写入题库失败: " + ex.Message;
        }
    }

    // ---- UI 绘制 ----

    /// <summary>独立预览线程：30fps 抓屏缩略后经 WriteableBitmap 增量上屏（WPF 走 DirectX 合成，画面与游戏同步）。
    /// 画面静止时（连续 3 帧像素戳相同）降频到 10fps 采样且跳过缩放/上屏，显著降低静止 CPU。</summary>
    private void PreviewLoop(ScreenSource source, CancellationToken ct)
    {
        long lastTick = 0;
        ulong lastStamp = 0;
        int staticFrames = 0;
        while (!ct.IsCancellationRequested)
        {
            long periodMs = staticFrames >= 3 ? 100 : 1000 / PreviewFps;
            long now = Environment.TickCount64;
            long wait = periodMs - (now - lastTick);
            if (wait > 0) { Thread.Sleep((int)wait); continue; }
            lastTick = Environment.TickCount64;
            try
            {
                var (full, _) = ScreenCapture.Capture(source);
                using (full)
                {
                    ulong stamp = PixelStamp(full);
                    if (stamp == lastStamp)
                    {
                        staticFrames++;
                        continue;
                    }
                    staticFrames = 0;
                    lastStamp = stamp;
                    UpdatePreview(full);
                }
            }
            catch (OperationCanceledException) { break; }
            catch { /* 截图瞬时失败忽略，下一帧重试 */ }
        }
    }

    /// <summary>缩略一帧并拷贝到 UI 线程的 WriteableBitmap（Bitmap 锁定期内完成上屏，随后在后台解锁释放）。</summary>
    private void UpdatePreview(System.Drawing.Bitmap full)
    {
        const int maxW = 800;
        double thumbScale = Math.Min(1.0, (double)maxW / full.Width);
        int pw = Math.Max((int)(full.Width * thumbScale), 1);
        int ph = Math.Max((int)(full.Height * thumbScale), 1);
        using var thumb = new System.Drawing.Bitmap(pw, ph, PixelFormat.Format32bppArgb);
        using (var g = Graphics.FromImage(thumb))
        {
            g.DrawImage(full, 0, 0, pw, ph);
        }
        var bd = thumb.LockBits(new Rectangle(0, 0, pw, ph), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try
        {
            Dispatcher.Invoke(() => DrawPreviewFrame(pw, ph, bd.Scan0, bd.Stride, thumbScale));
        }
        finally { thumb.UnlockBits(bd); }
    }

    private void DrawPreviewFrame(int pw, int ph, IntPtr scan0, int stride, double thumbScale)
    {
        double cw = PreviewCanvas.ActualWidth, ch = PreviewCanvas.ActualHeight;
        if (cw <= 0 || ch <= 0) return;
        if (_previewBitmap == null || _previewBitmap.PixelWidth != pw || _previewBitmap.PixelHeight != ph)
        {
            _previewBitmap = new WriteableBitmap(pw, ph, 96, 96, PixelFormats.Bgra32, null);
            if (_previewImage == null)
            {
                _previewImage = new System.Windows.Controls.Image { Stretch = Stretch.Fill };
                PreviewCanvas.Children.Add(_previewImage);
            }
            _previewImage.Source = _previewBitmap;
        }
        _previewBitmap.WritePixels(new Int32Rect(0, 0, pw, ph), scan0, stride * ph, stride);

        double canvasScale = Math.Min(Math.Min(cw / pw, ch / ph), 1.0);
        double dispW = pw * canvasScale, dispH = ph * canvasScale;
        double ox = (cw - dispW) / 2, oy = (ch - dispH) / 2;
        // 原图 → 画布总缩放 = 缩略缩放 × 画布缩放
        _previewScale = thumbScale * canvasScale;
        _previewOffset = (ox, oy);
        _previewDispSize = (dispW, dispH);

        if (_previewImage == null) return;
        WpfCanvas.SetLeft(_previewImage, ox);
        WpfCanvas.SetTop(_previewImage, oy);
        _previewImage.Width = dispW;
        _previewImage.Height = dispH;
        DrawZones();
    }

    /// <summary>按当前 ROI 重画题目/图标框(绿)与选项框(蓝)；拖拽与每帧渲染共用。</summary>
    private void DrawZones()
    {
        var (dispW, dispH) = _previewDispSize;
        if (dispW <= 0 || _previewImage == null) return;
        var (ox, oy) = _previewOffset;
        UpdateZoneRect(ref _qZoneRect, _qRoi, QuestionZoneColor, dispW, dispH, ox, oy);
        UpdateZoneRect(ref _oZoneRect, _oRoi, OptionZoneColor, dispW, dispH, ox, oy);
    }

    private void UpdateZoneRect(
        ref System.Windows.Shapes.Rectangle? rect, Roi roi, System.Windows.Media.Color color,
        double dispW, double dispH, double ox, double oy)
    {
        if (rect == null)
        {
            rect = new System.Windows.Shapes.Rectangle
            {
                Stroke = new SolidColorBrush(color),
                StrokeThickness = 2,
            };
            PreviewCanvas.Children.Add(rect);
        }
        rect.Width = dispW * roi.W / 100;
        rect.Height = dispH * roi.H / 100;
        WpfCanvas.SetLeft(rect, ox + dispW * roi.X / 100);
        WpfCanvas.SetTop(rect, oy + dispH * roi.Y / 100);
    }

    private void DrawAnswerBox(double ax, double ay, double aw, double ah, double left, double right, Rectangle fullRect)
    {
        if (_previewImage == null) return;
        // 整图坐标 -> 预览画布坐标（复用 DrawPreviewFrame 计算的缩放/偏移，保证与画面完全对齐）
        double scale = _previewScale;
        (double ox, double oy) = _previewOffset;

        double x1 = ox + (ax - aw / 2 + aw * left) * scale;
        double y1 = oy + (ay - ah / 2) * scale;
        double x2 = ox + (ax - aw / 2 + aw * right) * scale;
        double y2 = oy + (ay + ah / 2) * scale;

        if (_answerRect == null)
        {
            _answerRect = new System.Windows.Shapes.Rectangle
            {
                Stroke = new SolidColorBrush(AnswerColor),
                StrokeThickness = 3,
            };
            PreviewCanvas.Children.Add(_answerRect);
        }
        _answerRect.Width = Math.Max(x2 - x1, 4);
        _answerRect.Height = Math.Max(y2 - y1, 4);
        WpfCanvas.SetLeft(_answerRect, x1);
        WpfCanvas.SetTop(_answerRect, y1);
        _answerRect.Visibility = Visibility.Visible;
    }

    private static System.Drawing.Bitmap Crop(System.Drawing.Bitmap src, Rectangle r)
    {
        r.Intersect(new Rectangle(0, 0, src.Width, src.Height));
        if (r.Width <= 0 || r.Height <= 0) return new System.Drawing.Bitmap(1, 1);
        return src.Clone(r, PixelFormat.Format32bppArgb);
    }

    private static string ComputeHash(System.Drawing.Bitmap bmp)
    {
        // 8x8 感知哈希
        var small = new System.Drawing.Bitmap(bmp, 9, 8);
        long bits = 0;
        for (int y = 0; y < 8; y++)
            for (int x = 0; x < 8; x++)
            {
                int a = small.GetPixel(x, y).GetBrightness() > 0.5 ? 1 : 0;
                int b = small.GetPixel(x + 1, y).GetBrightness() > 0.5 ? 1 : 0;
                bits = (bits << 1) | (uint)(a < b ? 1 : 0);
            }
        small.Dispose();
        return bits.ToString("X");
    }

    private static bool IsUiNoise(string text)
    {
        text = text.Trim();
        if (text.Length <= 1) return true;
        if (text.Contains("题目：")) return false;
        return System.Text.RegularExpressions.Regex.IsMatch(text,
            @"离开答题|当前第\s*\d|还可以答|附加考题?|附加题|第\d+题"
            + @"|连对|科举大赛第?\s*\d*\s*关|这一关考的是|殿试部分"
            + @"|[吏户礼兵刑工]部考题|已答\d+题|答对\d+题");
    }
}

