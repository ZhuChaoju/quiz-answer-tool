# Quiz Answer Tool（多活动答题识别展示工具）

Windows 桌面答题识别辅助工具：**多活动模块化**（科举乡试/会试、教师节看图说话、元宵节灯谜，可扩展），
选定窗口或屏幕 → 按活动预设的识别区域截屏 → RapidOCR/图标哈希识别 → 本地题库/素材库匹配 →
预览红框标出正确选项 + 可挪动的置顶答题浮窗，由人工点击作答。**只做展示，绝不向游戏发送任何输入。**

## 免责声明（必读）

**本项目为非商用、仅学习交流用途的自动化工具，与任何游戏、网站或平台的官方均无任何关联。**

使用本项目即表示你已知悉并同意以下内容：

1. **风险自负**：请自行评估使用场景的合规性。用于游戏等在线场景时，可能违反对应平台的服务条款，**存在封号、封禁或法律风险**，一切后果由使用者自行承担，项目作者不承担任何责任。
2. **非商用**：本项目仅用于个人学习与技术交流，禁止用于任何商业用途。
3. **不包含任何内容素材**：本仓库**不含任何题库数据、截图、游戏素材或受版权保护的内容**（均已 gitignore，永不提交）。`banks/` 下的题库/素材需用户自行获取并放在本地。
4. **数据合规由使用者负责**：使用者自行获取、整理题库/素材时，应确保数据来源合法、不侵犯任何第三方权益；由此引发的任何纠纷与项目作者无关。
5. **禁止违规使用**：请勿将本项目用于任何违反法律法规、平台服务条款或侵犯他人权益的场景。
6. **技术中立**：本项目仅提供通用屏幕识别、OCR 与本地数据匹配等基础技术能力，不针对任何特定游戏、网站或服务进行适配；工具的实际用途由使用者决定。

## 功能

- **活动模块化**：`banks/` 下每个活动一个文件夹，各自绑定题库（图片活动即素材库）与识别区域预设；下拉切换，互不干扰
  - `banks/keju/`　科举（乡试、会试格式不同，两个模块共享一个题库）
  - `banks/teachers/`　教师节·看图说话（题目是技能图标 → 官网素材库哈希匹配）
  - `banks/yuanxiao/`　元宵节·灯谜
- **实时预览**：30fps 增量渲染；可切换「只显示识别区域」放大查看
- **识别区域**：每个活动独立预设（百分比坐标自适应分辨率/缩放），**可锁定防误触**；解锁后可拖动/缩放，「保存为预设」写回模块配置；裁剪自带 2% 外扩容错
- **抗挪动**：教师节模块在搜索窗内连通域自动定位题目标图，游戏内答题框被拖动后仍能锁定图标
- **快速识别**：RapidOCR PP-OCRv6 tiny，题目/选项双引擎并行，端到端约 220~300ms；画面未变化时哈希闸门直接跳过（零开销）
- **答案红框**：预览红框精确圈出正确选项（175dt 样式）；「答题浮窗」置顶显示题目与红框答案，**可拖动挪位**（按活动记忆位置），可开鼠标穿透
- **答案录入**：未命中/错题当场录入，文字题写回题库、图标连同哈希写回图标库，越用越全

## 使用

1. 双击 `quiz-answer-tool.exe`（与 `banks/`、`config.json` 同目录；发布包 `dist/release/` 已组装好，双击即用）
2. 顶部选活动与画面来源（默认按 `window_keyword: 梦幻西游` 自动选中游戏窗口），点「开始」
3. 正常情况无需调整：识别区域已按活动锁定预设；若游戏内答题框被挪动/分辨率变化，解锁后拖框校准，「保存为预设」
4. 看到浮窗/预览答案后人工点击作答；未命中时在录入框输入正确答案点「收录」

### 打包为 exe

```bat
build_exe.bat
```

产物：`dist/quiz-answer-tool.exe` 与 `dist/release/`（exe + banks + config 整包）。改完代码必须重新打包。

## 题库/素材库准备（banks/ 目录结构）

```
banks/
  keju/                     科举题库
    questions.json            4330 题 [{id,question,options,answer}]
    modules/
      keju_xiangshi.json      乡试模块（ROI 预设、题面前缀规则、噪声行）
      keju_huishi.json        会试模块
  teachers/                 教师节素材库
    icons/                    官网技能图标（来源 xyq.163.com，网易官方 CDN）
    icons.json                name → 256位梯度哈希 索引（tools/build_icon_bank.py 生成）
    module.json
  yuanxiao/                 元宵节题库
    questions.json            838 题
    module.json
```

- **新增活动** = banks 下新建子目录（`module.json` 或 `modules/*.json`）+ 题库/素材，重启即出现在活动下拉
- 文字题库转换：`python tools/keju_to_questions.py keju_tiku.txt -o banks/keju/questions.json`（sqlite 题库用 `tools/db_to_questions.py`）
- 图标库重建：`python tools/build_icon_bank.py <icons目录>`

### 模块配置字段（module.json）

```jsonc
{
  "id": "keju_huishi", "name": "科举·会试", "type": "text",   // text=文字题 / icon=看图说话
  "bank": "questions.json",                                    // 相对 banks/<库>/；icon 模块用 "icon_bank"
  "question_anchor": "题目\\s*[:：]",                           // 题面锚点（截掉关卡前缀）
  "noise": ["这一关考的是"],                                    // 追加噪声行正则
  "roi": {                                                     // 百分比坐标 {x,y,w,h}
    "question": {}, "option": {},
    "icon": {}, "search": {}                                   // icon 模块：图标区 + 自动定位搜索窗
  },
  "locked": true                                               // 默认锁定状态
}
```

## 测试（改完代码跑一遍）

```bash
.venv\Scripts\python -X utf8 tools\test_text_modules.py   # 科举乡试/会试+元宵 端到端（真实网图+合成题图）
.venv\Scripts\python -X utf8 tools\test_icon_module.py    # 教师节 9 张真实截图（4 张带 175dt 真值）
.venv\Scripts\python -X utf8 tools\test_gui_smoke.py      # 主窗口/浮窗/渲染冒烟
.venv\Scripts\python -X utf8 tools\test_live_loop.py      # 实况双线程 6 秒冒烟
```

基线：文字模块 4/4；教师节真值 4/4、9 图全部定位并给出红框；端到端 220~300ms（tiny）。

## 配置（config.json）

```json
{
  "interval_sec": 0.2,
  "window_keyword": "梦幻西游",
  "ocr": {"lang": "ch", "confidence": 0.4, "model_type": "tiny", "use_dml": false},
  "ui": {"module": "teachers", "roi_only": false, "overlay": true, "locked": {}, "overlay_pos": {}}
}
```

- `interval_sec`：识别轮询间隔，画面未变时只有哈希开销
- `ocr.model_type`：`tiny`（默认 ~220ms）/ `small` / `medium`；`use_dml` 需 `onnxruntime-directml`
- `ui.overlay_pos`：答题浮窗按活动记忆的位置

## License

MIT
