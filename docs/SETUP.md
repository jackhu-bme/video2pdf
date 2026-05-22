# video2pdf 配置与使用

这个仓库用于在 Codex 本地环境中安装视频转 PDF 讲义相关 skills：

- `youtube-render-pdf`：处理 YouTube 长视频、课程、技术讲座。
- `bilibili-render-pdf`：处理 Bilibili 长视频、分 P 视频，必要时用 Whisper 转写。
- `subtitle-refine`：精修中文 SRT 字幕。

## 1. 安装 skills

在仓库根目录执行：

```bash
mkdir -p ~/.codex/skills
cp -R skills/youtube-render-pdf ~/.codex/skills/
cp -R skills/bilibili-render-pdf ~/.codex/skills/
cp -R skills/subtitle-refine ~/.codex/skills/
```

如果之后改了 skill 内容，重新复制覆盖即可：

```bash
rm -rf ~/.codex/skills/youtube-render-pdf \
  ~/.codex/skills/bilibili-render-pdf \
  ~/.codex/skills/subtitle-refine

cp -R skills/youtube-render-pdf ~/.codex/skills/
cp -R skills/bilibili-render-pdf ~/.codex/skills/
cp -R skills/subtitle-refine ~/.codex/skills/
```

## 2. 安装系统依赖

macOS 推荐用 Homebrew：

```bash
brew install yt-dlp ffmpeg imagemagick
brew install --cask mactex
```

Bilibili 无 CC 字幕时还需要 Whisper：

```bash
python3 -m pip install -U openai-whisper
```

安装后检查：

```bash
yt-dlp --version
ffmpeg -version
magick -version
xelatex --version
whisper --help
```

## 3. 配置 API Key

推荐把文本模型和视觉模型分开配置：文本走 DeepSeek V4，关键帧理解走 Kimi。

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
TEXT_BASE_URL=https://api.deepseek.com
TEXT_API_KEY=your_deepseek_api_key
TEXT_MODEL=deepseek-v4-flash
TEXT_STRONG_MODEL=deepseek-v4-pro

VISION_BASE_URL=https://api.moonshot.ai/v1
VISION_API_KEY=your_moonshot_api_key
VISION_MODEL=kimi-k2.6
```

如果 `kimi-k2.6` 暂时不可用，可以先把 `VISION_MODEL` 改成 `moonshot-v1-128k-vision-preview`。不要把 `.env` 或 API Key 提交到 Git。

中英混合视频的转写建议先用本地 Whisper 自动识别语言：

```bash
whisper audio.wav --model small --output_format srt --output_dir subtitles
```

如果术语或中文识别质量不够，再换：

```bash
whisper audio.wav --model medium --output_format srt --output_dir subtitles
```

## 4. Bilibili 高清与登录 cookies

Bilibili 的 1080P+ 通常需要登录态。建议先在 Chrome 登录 B 站，然后下载时让 `yt-dlp` 读取浏览器 cookies：

```bash
yt-dlp --cookies-from-browser chrome -F "https://www.bilibili.com/video/BV..."
```

如果是分 P 视频，先探测 metadata，再决定处理哪一 P 或哪些 P。

## 5. 在 Codex 中调用

YouTube 示例：

```text
$youtube-render-pdf https://www.youtube.com/watch?v=... 请生成结构化中文讲义和最终 PDF。长视频请按章节拆分。文本分段和最终整合用 DeepSeek V4，关键帧理解用 Kimi，多语言字幕优先用本地 Whisper 生成 SRT。
```

Bilibili 示例：

```text
$bilibili-render-pdf https://www.bilibili.com/video/BV... 请生成结构化中文讲义和最终 PDF。如无 CC 字幕，先用本地 Whisper 生成带时间戳的 SRT。文本分段和最终整合用 DeepSeek V4，关键帧理解用 Kimi。
```

长视频建议追加：

```text
请先检查 metadata、章节、字幕、分 P 情况和时长。超过 20 分钟请拆成多个段落处理，保留关键帧时间来源，最后整合成一份统一叙事的 PDF。
```

## 6. 推荐工作目录

每个视频建议单独建目录，避免素材混在一起：

```text
work/
  youtube-video-title/
    metadata.json
    subtitles/
    frames/
    figures/
    notes.tex
    notes.pdf
  bilibili-video-title/
    metadata.json
    subtitles/
    frames/
    figures/
    notes.tex
    notes.pdf
```

`work/` 可以保留在本地，不一定提交到仓库。

## 7. 常见问题

- YouTube 字幕下载失败：先用 `yt-dlp --list-subs URL` 查看可用字幕语言。
- Bilibili 没字幕：用 `whisper` 对音频转写，再把 SRT 作为主素材。
- PDF 编译失败：优先检查中文 TeX 环境、图片路径、LaTeX 特殊字符转义。
- 图片太糊：提高视频下载分辨率，或在关键区域 crop 后再插图。
- 长视频总结不完整：让 Codex 先分段抽取，再用独立复核 pass 检查遗漏。
