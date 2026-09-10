# Quiz Answer Tool (C# / .NET 8)

桌面答题识别辅助工具的 **C# 重写版**（v2）。基于 .NET 8 + WPF + RapidOcrNet（PP-OCRv6 中文模型），比 Python 版更快、CPU 占用更低。

> **免责声明（必读）**：本工具为非商用、仅学习交流用途，与任何游戏/平台官方无关联。用于游戏等在线场景可能违反平台服务条款，存在封号或法律风险，一切后果由使用者自行承担。本项目不含任何题库数据、截图或游戏素材（见下方"合规红线"）。

## 功能

- 实时预览游戏窗口画面（30fps 独立预览线程，WriteableBitmap 增量上屏，WPF 走 DirectX 合成，与游戏画面同步流畅）
- 自动检测并选中目标窗口（可在 config.json 配置 window_keyword）
- 固定 ROI：题目区（绿框）+ 选项区（蓝框），识别范围写死
- RapidOcrNet（PP-OCRv6，默认 tiny，可配 small/medium）识别：**纯内存**（不再经临时 PNG 落盘往返），题目 OCR 与选项 OCR **双引擎并行**
- 感知哈希闸门：题目区画面未变化时整轮跳过 OCR（静止画面零开销）
- 可选 DirectML GPU 推理（`ocr.use_dml`，ORT 1.27 原生库内置，无需额外包）
- 题库三级匹配：精确 → 子串 → 模糊（SequenceMatcher 块匹配，容错 OCR 错字）
- 答案红框精确定位（基于 OCR 文本框坐标）
- 答案录入：未命中时手动收录进题库，内存与 questions.json 双写（同题覆盖更新）

## 实测成绩（62 张真实截图）

- 旧版基线（small 模型 + PNG 落盘）：题目命中 60/62（96.8%），答案定位 58/60（96.7%），单题识别 ~420ms
- 当前版本改纯内存识别 + tiny 模型 + 哈希闸门 + 并行识别后待用 VerifyOcr 复测（tiny 同模型在 Python 版实测 ~178ms、97% 命中，可作参照）

## 环境要求

- Windows 10/11（x64）
- .NET 8 SDK（开发）/ 运行时（运行）

## 构建与运行

```bash
# 开发运行
dotnet run --project QuizAnswerTool

# 发布单文件 exe（self-contained，任意电脑免装 .NET）
dotnet publish QuizAnswerTool/QuizAnswerTool.csproj -c Release -r win-x64 \
  --self-contained true -p:PublishSingleFile=true \
  -p:IncludeNativeLibrariesForSelfExtract=true \
  -p:EnableCompressionInSingleFile=true -o publish
```

发布产物结构（`publish/`）：

```
quiz-answer-tool.exe          # 主程序（内置 .NET 运行时）
models/v6/                    # OCR 模型（需单独准备，见下）
config.json                   # 用户配置
questions.json                # 题库（需单独准备）
```

## 数据文件准备

1. **OCR 模型**（git 不提交）：从 RapidAI 官方下载 PP-OCRv6 模型到 `models/v6/`：
   - tiny 档（默认，最快）：`PP-OCRv6_det_tiny.onnx`、`PP-OCRv6_rec_tiny.onnx`、`ppocrv6_tiny_dict.txt`（注意 tiny 用**独立字典**）
   - small 档（回退/备用）：`PP-OCRv6_det_small.onnx`、`PP-OCRv6_rec_small.onnx`、`ppocrv6_dict.txt`
   - 公共：`cls.onnx`（方向分类，PP-OCRv5 mobile 版通用）
   - 下载源：https://www.modelscope.cn/models/RapidAI/RapidOCR （onnx/PP-OCRv6/ 目录）
   - 缺 tiny 文件时程序自动回退到 small，两者都在则由 `ocr.model_type` 决定
2. **题库**：`questions.json`（格式见下），从 `keju_tiku.txt` 转换（Python 版 `tools/keju_to_questions.py`）
3. **配置**：`config.json`（可从 `config.example.json` 复制）

```json
// questions.json 格式
[
  {"id": 1, "question": "题目文本", "options": [], "answer": "答案文本"}
]
```

```json
// config.json
{
  "interval_sec": 0.05,
  "question_roi": {"x": 30.0, "y": 31.0, "w": 45.0, "h": 14.0},
  "option_roi": {"x": 40.0, "y": 53.0, "w": 35.0, "h": 16.0},
  "window_keyword": "",
  "ocr": {"lang": "ch", "confidence": 0.4, "model_type": "tiny", "use_dml": false}
}
```

> ROI 为相对游戏窗口客户区的百分比。答题面板位置随游戏版本可能变化，需按实际截图标定。
> `ocr.model_type`：`tiny`（默认）/ `small` / `medium`；`ocr.use_dml`：true 时启用 DirectML GPU 推理
>（ORT 1.27 原生库已内置 DML EP，无需额外 NuGet 包），有独立显卡时可再快数倍。

## 项目结构

```
QuizAnswerTool/
├── App.xaml / MainWindow.xaml    # WPF 主界面
├── Core/
│   ├── ScreenCapture.cs          # 窗口枚举 + 客户区截图（Win32）
│   ├── WinOcr.cs                 # RapidOcrNet 封装（双引擎并行）
│   ├── QuestionBank.cs           # 题库加载 + 三级匹配
│   ├── AnswerLocator.cs          # 答案行定位（段坐标）
│   └── Config.cs                 # 配置加载
└── models/                       # OCR 模型（git 忽略，需手动下载）
```

## 合规红线（务必遵守）

- **`questions.json`、`config.json`、`keju_tiku.txt`、截图、`models/` 一律不提交 git**（.gitignore 已强制）
- 仓库不含任何题库数据、截图、游戏素材或受版权保护内容
- 分发 exe 时需用户自行准备题库与模型，与仓库无关

## 已知限制

- 2026-09-10 与 Python 版(main)的结构差异：活动切换在 MainWindow 内联 if/else（Python 为 banks/ 模块化装配）；
  OCR 未做折行合并（Python 有可配置 merge_lines），长题面折行后按单行匹配；
  AnswerLocator.Segments 为 (0,1) 占位比例（Python 已改为检测框绝对像素），红框精度与 Python 不一致；
  答案圈选已集中 AnswerLocator 静态类，与 Python base.py 依赖方向一致，无兄弟模块串扰
- 游戏画面持续动画时哈希闸门不生效，仍会按间隔 OCR（静止界面零开销）
- 未命中题目靠"答案录入"功能积累题库
- ROI 写死适配当前游戏版本布局，版本更新后需重新标定
