# Quiz Answer Tool

Windows 桌面答题识别辅助工具：选定窗口或屏幕 → 实时预览 → 框选题目区域 → OCR 识别 → 本地题库匹配 → 显示答案（红框标出答案位置），由人工点击作答。

## 免责声明（必读）

**本项目为非商用、仅学习交流用途的自动化工具，与任何游戏、网站或平台的官方均无任何关联。**

使用本项目即表示你已知悉并同意以下内容：

1. **风险自负**：请自行评估使用场景的合规性。用于游戏等在线场景时，可能违反对应平台的服务条款，**存在封号、封禁或法律风险**，一切后果由使用者自行承担，项目作者不承担任何责任。
2. **非商用**：本项目仅用于个人学习与技术交流，禁止用于任何商业用途。
3. **不包含任何内容素材**：本项目**不含任何题库数据、截图、游戏素材或受版权保护的内容**。题库需用户自行整理并放在本地（`questions.json`、`keju_tiku.txt` 等），且上述文件已被 `.gitignore` 排除、永不提交。
4. **数据合规由使用者负责**：使用者自行获取、整理题库时，应确保数据来源合法、不侵犯任何第三方权益；因题库数据引发的任何纠纷与项目作者无关。
5. **禁止违规使用**：请勿将本项目用于任何违反法律法规、平台服务条款或侵犯他人权益的场景。
6. **技术中立**：本项目仅提供通用屏幕识别、OCR 与本地数据匹配等基础技术能力，不针对任何特定游戏、网站或服务进行适配；工具的实际用途由使用者决定。

## 功能

- **实时预览**：窗口 2 以 60fps 显示所选窗口/屏幕画面
- **ROI 框选**：预览上拖拽绿色框，框内区域即识别范围（移动/缩放/重画，百分比坐标自适应分辨率）
- **快速识别**：RapidOCR（onnx 推理）识别 ROI 内文本，约 0.2s 出结果；题目未变化时自动跳过识别（零开销）
- **答案红框**：命中时在预览画面上用红框标出答案所在行
- **答案录入**：未命中/错题时输入正确答案，一键收录进本地题库（越用越全）
- 题目去重：相同题面不重复识别

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
python -m quiz_answer_tool run --questions questions.json
```

1. 顶部选择画面来源（游戏窗口或整个屏幕）
2. 拖动绿色 ROI 框包住题目区（如 800x600 游戏窗口的题目区域）
3. 点「开始」，答案自动显示在下方面板，红框标出位置
4. 看到答案后人工点击作答

## 打包为 exe（构建规范）

目标：改完代码后一键生成免环境 exe（含 Python 运行时与 RapidOCR 模型，~100MB），任意 Windows 电脑双击即用。

### 一键构建

```bat
build_exe.bat
```

### 手动构建步骤（build_exe.bat 等价命令）

```bash
# 1. 安装打包工具（首次）
pip install pyinstaller

# 2. 打包（onefile 单文件，含 RapidOCR 模型）
pyinstaller --onefile --name quiz-answer-tool --windowed ^
  --paths src ^
  --collect-all rapidocr_onnxruntime ^
  --hidden-import win32gui ^
  pack_launcher.py ^
  --distpath dist --workpath build --clean
```

### 产物与分发

- 产物：`dist/quiz-answer-tool.exe`
- 分发到目标电脑时，需把 `config.json`、`questions.json`（或 `config.example.json`）与 exe 放在**同一目录**
- exe 双击直接运行（`cli.py` 已支持无参数默认进入 run）；命令行 `quiz-answer-tool.exe run` 亦可

### 构建红线（务必遵守）

- **`dist/`、`build/`、`*.spec` 已被 `.gitignore` 排除，exe 一律不得提交/推送 git**
- 打包入口 `pack_launcher.py` 不能删除（负责模块启动与 windowed 模式 stderr 重定向）
- 改完代码后必须重新打包：`build_exe.bat`

## 题库准备

`keju_tiku.txt` → `questions.json`：

```bash
python tools/keju_to_questions.py keju_tiku.txt -o questions.json
```

`questions.json` 格式（answer 为答案文本）：

```json
[
  {"id": 1, "question": "……", "options": [], "answer": "答案文本"}
]
```

## 配置

复制 `config/config.example.json` 为 `config.json`：

```json
{
  "interval_sec": 0.2,
  "roi": {"x": 10, "y": 10, "w": 80, "h": 30},
  "ocr": {"lang": "ch", "confidence": 0.6}
}
```

- `interval_sec`：画面检测间隔（秒）。题目画面变化时才触发 OCR，变化后约 0.2s 内出答案
- `roi`：识别区域（占画面百分比），也可在预览中拖拽调整

## 工具

- `tools/keju_to_questions.py`：题库文本 → questions.json（自动去重）
- `tools/html_to_json.py`：通用 HTML → JSON 转换器（不绑定任何特定站点）

## License

MIT
