using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

namespace QuizAnswerTool.Core;

/// <summary>屏幕来源：窗口或整个屏幕。</summary>
public sealed class ScreenSource
{
    public string Id { get; init; } = "";
    public string Name { get; init; } = "";
    public string Kind { get; init; } = ""; // "window" | "monitor"
    public nint Hwnd { get; init; }
}

/// <summary>Win32 窗口枚举与截屏。</summary>
public static class ScreenCapture
{
    private const int SRCCOPY = 0x00CC0020;
    private const int PW_RENDERFULLCONTENT = 0x00000002;

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT { public int Left, Top, Right, Bottom; }

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, nint lParam);
    private delegate bool EnumWindowsProc(nint hWnd, nint lParam);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(nint hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(nint hWnd, char[] lpString, int nMaxCount);

    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(nint hWnd, out RECT lpRect);

    [DllImport("user32.dll")]
    private static extern bool GetClientRect(nint hWnd, out RECT lpRect);

    [StructLayout(LayoutKind.Sequential)]
    private struct POINT { public int X, Y; }

    [DllImport("user32.dll")]
    private static extern bool ClientToScreen(nint hWnd, ref POINT lpPoint);

    [DllImport("user32.dll")]
    private static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    private static extern bool PrintWindow(nint hWnd, nint hdcBlt, uint nFlags);

    [StructLayout(LayoutKind.Sequential)]
    private struct MONITORINFO
    {
        public int cbSize;
        public RECT rcMonitor;
        public RECT rcWork;
        public uint dwFlags;
    }

    private delegate bool MonitorEnumProc(nint hMonitor, nint hdcMonitor, ref RECT lprcMonitor, nint dwData);

    [DllImport("user32.dll")]
    private static extern bool EnumDisplayMonitors(nint hdc, nint lprcClip, MonitorEnumProc lpfnEnum, nint dwData);

    public static void EnableDpiAware()
    {
        try { SetProcessDPIAware(); }
        catch { /* ignore */ }
    }

    public static List<ScreenSource> ListSources()
    {
        var list = new List<ScreenSource>();
        var monitors = new List<Rectangle>();
        EnumDisplayMonitors(nint.Zero, nint.Zero, (nint _h, nint _dc, ref RECT rc, nint _d) =>
        {
            monitors.Add(new Rectangle(rc.Left, rc.Top, rc.Right - rc.Left, rc.Bottom - rc.Top));
            return true;
        }, nint.Zero);
        for (int i = 0; i < monitors.Count; i++)
        {
            list.Add(new ScreenSource
            {
                Id = $"monitor:{i}",
                Name = i == 0 ? "全部屏幕" : $"屏幕 {i + 1}",
                Kind = "monitor",
            });
        }
        EnumWindows((hWnd, _) =>
        {
            if (IsWindowVisible(hWnd))
            {
                var title = GetTitle(hWnd);
                if (!string.IsNullOrWhiteSpace(title))
                    list.Add(new ScreenSource { Id = $"window:{hWnd}", Name = title, Kind = "window", Hwnd = hWnd });
            }
            return true;
        }, nint.Zero);
        return list;
    }

    private static string GetTitle(nint hWnd)
    {
        var buf = new char[512];
        int len = GetWindowText(hWnd, buf, buf.Length);
        return len > 0 ? new string(buf, 0, len) : "";
    }

    /// <summary>抓取来源画面，返回 Bitmap（物理像素）与整图区域。</summary>
    public static (Bitmap Bitmap, Rectangle Rect) Capture(ScreenSource source)
    {
        if (source.Kind == "window")
        {
            if (!GetClientRect(source.Hwnd, out var crect))
                throw new InvalidOperationException($"无法获取客户区 (hwnd={source.Hwnd})");
            // 客户区原点的屏幕坐标：GetClientRect 的 Left/Top 恒为 0（客户坐标系），
            // 旧写法 wrect.Top + crect.Left 实际等于窗口矩形顶（含标题栏），
            // 导致截图像素整体下移一个标题栏高度、底部同高被裁掉
            var origin = new POINT { X = 0, Y = 0 };
            if (!ClientToScreen(source.Hwnd, ref origin))
                throw new InvalidOperationException($"无法换算客户区坐标 (hwnd={source.Hwnd})");
            var rc = new Rectangle(
                origin.X, origin.Y,
                crect.Right - crect.Left, crect.Bottom - crect.Top);
            if (rc.Width <= 0 || rc.Height <= 0)
                throw new InvalidOperationException("窗口尺寸无效");
            return (CaptureRegion(rc), rc);
        }
        else
        {
            int idx = int.Parse(source.Id.Split(':')[1]);
            // 从枚举结果重建（简单起见再次枚举）
            var monitors = new List<Rectangle>();
            EnumDisplayMonitors(nint.Zero, nint.Zero, (nint _h, nint _dc, ref RECT rc, nint _d) =>
            {
                monitors.Add(new Rectangle(rc.Left, rc.Top, rc.Right - rc.Left, rc.Bottom - rc.Top));
                return true;
            }, nint.Zero);
            if (idx >= monitors.Count)
                throw new InvalidOperationException("显示器索引无效");
            var bounds = monitors[idx];
            return (CaptureRegion(bounds), bounds);
        }
    }

    /// <summary>抓取指定屏幕区域（GDI BitBlt，物理像素）。</summary>
    public static Bitmap CaptureRegion(Rectangle rect)
    {
        var bmp = new Bitmap(rect.Width, rect.Height, PixelFormat.Format32bppArgb);
        using var g = Graphics.FromImage(bmp);
        g.CopyFromScreen(rect.Left, rect.Top, 0, 0, rect.Size, CopyPixelOperation.SourceCopy);
        return bmp;
    }

    /// <summary>按百分比区域裁剪图片。</summary>
    public static Rectangle CropRegion(Rectangle full, double x, double y, double w, double h)
    {
        int left = (int)(full.Width * x / 100.0);
        int top = (int)(full.Height * y / 100.0);
        int cw = (int)(full.Width * w / 100.0);
        int ch = (int)(full.Height * h / 100.0);
        return new Rectangle(left, top, cw, ch);
    }
}
