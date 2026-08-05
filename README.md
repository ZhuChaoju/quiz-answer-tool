# Quiz Answer Tool

Windows 桌面答题识别辅助工具：选定窗口或屏幕 → 实时预览 → 框选题目区域 → OCR 识别 → 本地题库匹配 → 显示答案（红框标出答案位置），由人工点击作答。

## 免责声明（必读）

- 本项目为**学习交流用途**的自动化工具，非官方工具。
- 请自行评估使用场景合规性；用于游戏等在线场景**存在封号风险**，后果自负。
- 本项目**不包含任何题库数据、截图或游戏素材**，题库需用户自行整理并放入本地（`questions.json`），且已被 `.gitignore` 排除。
- 请勿用于任何违反服务条款的场景。

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
