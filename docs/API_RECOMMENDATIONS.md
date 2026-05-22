# API 使用建议

更新时间：2026-05

这个仓库的目标是把 YouTube/Bilibili 长视频转换成结构化中文讲义和 PDF。当前推荐优先使用本地 Whisper、Kimi 多模态和 DeepSeek V4 文本模型，避免强依赖不方便付款的 GPT/Gemini API。工作流拆成四层：素材获取、转写、视觉理解、写作整合。

## 推荐架构

1. 素材获取：本地用 `yt-dlp` 下载 metadata、字幕、封面、音频和视频片段。
2. 转写：优先平台字幕；没有字幕时用本地 `openai-whisper`。
3. 视觉理解：从视频抽取关键帧，用 Kimi vision 判断图表、代码、公式和幻灯片内容。
4. 写作整合：用 DeepSeek V4 做分段抽取、全局 outline、章节写作、一致性复核和最终 LaTeX 生成。

## 默认模型组合

| 环节 | 推荐 | 说明 |
| --- | --- | --- |
| 长视频分段理解 | `deepseek-v4-flash` | 便宜、快、长上下文，适合字幕分块摘要和章节草稿。 |
| 最终写作与复核 | `deepseek-v4-pro` | 用在最终整合、缺漏复核、难内容解释。 |
| 中英混合转写 | 本地 `openai-whisper` 的 `small` 或 `medium` | M1 Mac 可跑；先用 `small`，质量不足再换 `medium`。 |
| 图片/关键帧理解 | `kimi-k2.6` | 用于截图、幻灯片、公式、代码和图表理解。 |
| Kimi vision fallback | `moonshot-v1-128k-vision-preview` | 如果账号暂时没有 `kimi-k2.6`，先用旧 vision preview。 |

## OpenAI-Compatible 配置

Kimi 和 DeepSeek 都支持 OpenAI-compatible HTTP API。项目里建议不要写死 `OPENAI_API_KEY`，而是分开配置文本模型和视觉模型：

```bash
TEXT_BASE_URL=https://api.deepseek.com
TEXT_API_KEY=your_deepseek_api_key
TEXT_MODEL=deepseek-v4-flash
TEXT_STRONG_MODEL=deepseek-v4-pro

VISION_BASE_URL=https://api.moonshot.ai/v1
VISION_API_KEY=your_moonshot_api_key
VISION_MODEL=kimi-k2.6
```

对应 Python 写法：

```python
from openai import OpenAI

text_client = OpenAI(
    api_key=os.environ["TEXT_API_KEY"],
    base_url=os.environ["TEXT_BASE_URL"],
)

vision_client = OpenAI(
    api_key=os.environ["VISION_API_KEY"],
    base_url=os.environ["VISION_BASE_URL"],
)
```

分工建议：

- 分段抽取：每 10 到 20 分钟一个 segment，输入字幕片段和少量关键帧说明。
- 结构化输出：让 DeepSeek 输出 JSON，包括教学目标、核心概念、公式、代码、需要保留的图、疑点。
- 关键帧理解：让 Kimi 输出“画面实际内容、是否完整可读、适合章节、图注、时间脚注”。
- 最终整合：把分段 JSON 和 Kimi 图像说明汇总成统一 outline，再写 LaTeX。

## 音频转写策略

优先级：

1. YouTube/Bilibili 原生字幕，保留时间戳。
2. 本地 `openai-whisper`，适合中英混合长视频和批量试跑。
3. 如果某段音频质量很差，再考虑人工校对或单独重跑更大的 Whisper 模型。

中英混合建议先不要固定 `--language zh`，让 Whisper 自动识别语言；如果中文占绝大多数且英文术语较少，再手动指定 `--language zh`。

```bash
whisper audio.wav --model small --output_format srt --output_dir subtitles
whisper audio.wav --model medium --output_format srt --output_dir subtitles
```

## 视觉输入策略

不要把整段视频作为单个输入。更稳的做法：

1. 用字幕时间戳定位概念附近时间窗。
2. 用 `ffmpeg` 抽多张候选帧。
3. 先做 contact sheet 人工或模型初筛。
4. 对最终候选帧调用 Kimi vision，输出“画面实际可见内容、是否完整、适合放在哪个章节、图注、时间脚注”。

幻灯片、公式、代码截图要优先可读性。宁可少送几张高质量候选图，也不要把整段视频密集抽帧全送给多模态模型。

## 成本控制

- 字幕和 metadata 先本地处理，尽量减少送入模型的原始噪声。
- 长视频先用 `deepseek-v4-flash` 做粗分段，再把关键段落和最终整合交给 `deepseek-v4-pro`。
- 固定的 system prompt、LaTeX 模板、写作规范放在输入前部，利用 prompt caching。
- 只把候选关键帧送给 Kimi vision，不要每隔几秒全量送图。

## 最小可用环境变量

```bash
cp .env.example .env
```

然后在 `.env` 中填入 DeepSeek 和 Moonshot/Kimi 的 API Key。不要把 `.env` 提交到 Git。

## 建议落盘产物

```text
metadata.json
source.srt
transcript.clean.srt
segments/*.json
frames/raw/*.jpg
frames/selected/*.jpg
figures/*.pdf
notes.tex
notes.pdf
review.md
```

这样后续可以断点续跑，也方便独立复核是否漏掉重要内容。
