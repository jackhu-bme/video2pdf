# API 使用建议

更新时间：2026-05

这个仓库的目标是把 YouTube/Bilibili 长视频转换成结构化中文讲义和 PDF。推荐把工作流拆成四层：素材获取、转写、视觉理解、写作整合。

## 推荐架构

1. 素材获取：本地用 `yt-dlp` 下载 metadata、字幕、封面、音频和视频片段。
2. 转写：优先平台字幕；没有字幕时用 OpenAI Transcription API 或本地 Whisper。
3. 视觉理解：从视频抽取关键帧，使用支持图片输入的模型判断图表、代码、公式和幻灯片内容。
4. 写作整合：用 Responses API 做分段抽取、全局 outline、章节写作、一致性复核和最终 LaTeX 生成。

## 默认模型组合

| 环节 | 推荐 | 说明 |
| --- | --- | --- |
| 长视频分段理解与最终写作 | `gpt-5.5` via Responses API | 适合长上下文、复杂写作、工具调用、多轮整合。 |
| 成本敏感的分段初筛 | `gpt-5.4-mini` 或 `gpt-5 mini` | 用于粗 outline、字幕分块摘要、候选关键帧初筛。 |
| 高质量语音转写 | `gpt-4o-transcribe` | 准确率优先，适合正式讲义素材。 |
| 低成本语音转写 | `gpt-4o-mini-transcribe` | 长视频批处理时更省。 |
| 说话人区分 | `gpt-4o-transcribe-diarize` | 访谈、圆桌、多人课程时使用。 |
| 图片/关键帧理解 | `gpt-5.5` 或支持 vision 的后续 GPT 模型 | 对关键帧使用 `detail: "high"` 或必要时 `original`。 |

## Responses API 用法

优先使用 Responses API，而不是把所有逻辑堆到 Chat Completions：

- 分段抽取：每 10 到 20 分钟一个 segment，输入字幕片段和候选关键帧。
- 结构化输出：让模型输出 JSON，包括教学目标、核心概念、公式、代码、需要保留的图、疑点。
- 最终整合：把分段 JSON 汇总成统一 outline，再写 LaTeX。
- 长任务：异步生成可用 background mode。
- 多轮状态：需要连续迭代时用 `previous_response_id` 或显式回放必要上下文。

## 音频转写策略

优先级：

1. YouTube/Bilibili 原生字幕，保留时间戳。
2. OpenAI Transcription API，优先 `gpt-4o-transcribe`。
3. 本地 `openai-whisper`，适合不想走 API 或批量试跑。

访谈类视频建议用 diarization；课程类单人讲授一般不需要。

## 视觉输入策略

不要把整段视频作为单个输入。更稳的做法：

1. 用字幕时间戳定位概念附近时间窗。
2. 用 `ffmpeg` 抽多张候选帧。
3. 先做 contact sheet 人工或模型初筛。
4. 对最终候选帧调用 vision 模型，输出“画面实际可见内容、是否完整、适合放在哪个章节、图注、时间脚注”。

幻灯片、公式、代码截图要优先可读性。默认用 `detail: "high"`；遇到密集图表时再用 `original`。

## 成本控制

- 字幕和 metadata 先本地处理，尽量减少送入模型的原始噪声。
- 长视频先用便宜模型做粗分段，再把关键段落交给强模型。
- 固定的 system prompt、LaTeX 模板、写作规范放在输入前部，利用 prompt caching。
- 最终整合和复核才用高 reasoning effort；普通分段抽取通常 `low` 或 `medium` 足够。
- 只把候选关键帧送给 vision，不要每隔几秒全量送图。

## 最小可用环境变量

```bash
export OPENAI_API_KEY="sk-..."
```

可选：

```bash
export OPENAI_PROJECT="proj_..."
export OPENAI_ORG_ID="org_..."
```

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
