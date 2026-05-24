# 短视频测试全过程记录（2026-05-24）

测试日期：2026-05-24（Asia/Shanghai）  
测试仓库：`/Users/hyq/Documents/video summary/repository/video2pdf`  
测试目录：`/Users/hyq/Documents/video summary/repository/video2pdf/work/test-youtube-lTcOkFg4geg`  
测试视频：`https://www.youtube.com/watch?v=lTcOkFg4geg`  
视频标题：`当我连续两把排到同一个对手`  
时长：`324s`（约 5m24s）  
上传者：`峡谷混学家`

## 1. 测试目标

验证简化版端到端链路是否可用：

1. 拉取 metadata、封面、字幕/音频、视频
2. Whisper 转写
3. 抽帧与 contact sheet
4. 模型调用：DeepSeek（文本）、Moonshot/Kimi（视觉）
5. 产出 `notes.tex` 并编译 `notes.pdf`

## 2. 素材获取

### 2.1 metadata + 封面 + 字幕探测

```bash
yt-dlp --write-info-json --write-thumbnail \
  --write-subs --write-auto-subs --sub-langs "zh.*,en.*" \
  --convert-subs srt --skip-download \
  -o "%(title)s.%(ext)s" "https://www.youtube.com/watch?v=lTcOkFg4geg"
```

产物（关键）：

- `当我连续两把排到同一个对手.info.json`
- `当我连续两把排到同一个对手.webp`

### 2.2 音频下载（用于 Whisper）

```bash
yt-dlp -x --audio-format wav -o "audio.%(ext)s" "https://www.youtube.com/watch?v=lTcOkFg4geg"
```

产物：

- `audio.wav`

## 3. Whisper 转写

命令（中英混合，语言自动）：

```bash
whisper audio.wav --model small --output_format srt --output_dir subtitles
```

产物：

- `subtitles/audio.srt`

观察：

- 可用，但存在 ASR 错字（游戏口播常见），后续可接 `subtitle-refine` 或提高模型等级。

## 4. 视频下载与抽帧

### 4.1 下载测试视频（720p）

```bash
yt-dlp -f "bv*[height<=720]+ba/b[height<=720]" --merge-output-format mp4 \
  -o "video.%(ext)s" "https://www.youtube.com/watch?v=lTcOkFg4geg"
```

产物：

- `video.mp4`

### 4.2 抽帧（每 30 秒 1 帧）

```bash
ffmpeg -i video.mp4 -vf "fps=1/30,scale=1280:-1" frames/frame_%03d.jpg
```

结果：

- 生成 11 张帧：`frame_001.jpg` ~ `frame_011.jpg`

## 5. Contact Sheet

初次报错：

- `montage: unable to read font ...`

修复后命令：

```bash
magick montage frames/*.jpg -font Helvetica -thumbnail 320x180 -geometry +8+8 contact_sheet.jpg
```

产物：

- `contact_sheet.jpg`（约 116KB）

## 6. 模型调用测试

### 6.1 DeepSeek 文本调用

状态：成功。  
用途：读取 SRT 做剧情/内容总结，输出结构化摘要。

### 6.2 Moonshot/Kimi 视觉调用

初期问题：

- `KeyError: 'VISION_API_KEY'`（shell 未导出 `.env`）
- `401 Invalid Authentication`（Moonshot 鉴权/余额问题）

修复：

1. 使用可导出方式加载 `.env`：
   ```bash
   set -a
   source ../../.env
   set +a
   ```
2. 校正 `VISION_BASE_URL` 与 API key，并完成账户可用性确认（含余额/权限）。

最终状态：成功。

## 7. 测试目录产物（关键文件）

- `audio.wav`
- `video.mp4`
- `subtitles/audio.srt`
- `frames/frame_001.jpg` ... `frames/frame_011.jpg`
- `contact_sheet.jpg`
- `当我连续两把排到同一个对手.info.json`
- `当我连续两把排到同一个对手.webp`

## 8. 结果判断

本次测试已通过“简化版”端到端验证：

- 工具链可用：`yt-dlp` / `ffmpeg` / `whisper` / `magick` / `xelatex`
- 模型链可用：DeepSeek 文本 + Moonshot/Kimi 视觉
- 可以进入“自动生成 `notes.tex` + 编译 `notes.pdf`”阶段

## 9. 已知局限（当前测试）

1. 视频类型为游戏解说，不是讲义类课程，不能代表正式课程 PDF 的内容质量上限。  
2. 仅做短视频冒烟，未覆盖长视频分段并行与全局一致性复核。  
3. Whisper 字幕未经 `subtitle-refine`，术语和错字仍可能影响总结质量。

## 10. 下一步建议

1. 固化脚本：新增 `scripts/render_video_pdf.py`，串联下载、转写、抽帧、模型调用、LaTeX 编译。  
2. 增加复核：引入二次检查回合，基于原字幕核对漏召回。  
3. 扩展长视频：按章节分段处理，并在最终合并时统一术语和章节结构。  
4. 增加配置：将模型名、分段长度、抽帧密度、编译参数都做成可配置项。
