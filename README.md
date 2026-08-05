# Quiz Answer Tool

Windows 桌面答题辅助工具：选定目标窗口后，自动抓取屏幕固定区域 → OCR 识别题目 → 本地题库匹配 → 模拟点击答案。

## 免责声明（必读）

- 本项目为**学习交流用途**的自动化工具，非官方工具。
- 请自行评估使用场景合规性；用于游戏等在线场景**存在封号风险**，后果自负。
- 本项目**不包含任何题库数据、截图或游戏素材**，题库需用户自行整理并放入本地（`questions.json`），且已被 `.gitignore` 排除。
- 请勿用于任何违反服务条款的场景。

## 功能

- 窗口选择：按标题关键词匹配目标窗口，支持窗口移动/缩放自适应
- 区域抓取：按窗口客户区百分比坐标抓取题目区与选项区
- OCR：PaddleOCR 中文识别
- 匹配：精确 → 子串 → 模糊三级匹配
- 执行：相对坐标换算屏幕绝对坐标，模拟点击
- 快捷键：`F8` 切换启停（可配置）

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```bash
# 查看窗口列表
python -m quiz_answer_tool list-windows

# 校准区域（截图预览 → 输入百分比坐标 → 写 config.json）
python -m quiz_answer_tool calibrate

# 运行（F8 启停）
python -m quiz_answer_tool run
```

## 配置

复制 `config/config.example.json` 为 `config.json` 并按需修改：

```json
{
  "window_title_keyword": "",
  "hotkey": "f8",
  "interval_sec": 0.5,
  "region_question": {"x": 10, "y": 60, "w": 80, "h": 20},
  "region_options":  {"x": 10, "y": 80, "w": 80, "h": 15},
  "ocr": {"lang": "ch", "confidence": 0.6}
}
```

区域坐标为窗口客户区**百分比**（0-100），窗口缩放时自动适配。

## 题库格式

`questions.json`（与 `questions.example.json` 同结构，示例仅含自造数据）：

```json
[
  {"id": 1, "question": "……", "options": ["A", "B", "C", "D"], "answer": "B"}
]
```

## 工具

`tools/html_to_json.py`：通用 HTML → JSON 转换器，用于把网页题面解析为题库格式（不绑定任何特定站点）。

## 验证

无真实场景时可运行 `--dry-run` 模式：合成测试图 → 截图 → OCR → 匹配 → 仅输出答案，不执行点击。

## License

MIT
