# 环境配置记录（M1 Mac）

更新时间：2026-05-24  
仓库路径：`/Users/hyq/Documents/video summary/repository/video2pdf`  
Conda 环境：`yt_pdf`

## 1. 目标

为 `video2pdf` 项目准备可复现的本地运行环境，支持：

- YouTube/Bilibili 素材下载（`yt-dlp`）
- 音视频处理与抽帧（`ffmpeg`）
- 图片处理（`ImageMagick`）
- 本地语音转写（`openai-whisper`）
- LaTeX 编译 PDF（`xelatex`）
- 模型调用（DeepSeek 文本 + Moonshot/Kimi 视觉）

## 2. 基础环境

### 2.1 Conda 环境

```bash
conda create -n yt_pdf python=3.10 -y
conda activate yt_pdf
```

### 2.2 Python 依赖

```bash
python -m pip install -U pip
python -m pip install -U openai-whisper openai python-dotenv yt-dlp
```

### 2.3 系统工具

```bash
conda install -c conda-forge ffmpeg -y
brew install imagemagick
```

说明：`imagemagick` 在默认 Anaconda/SJTU 镜像频道可能不可用，改用 `conda-forge` 或 `brew` 更稳。

## 3. 关键问题与修复

### 3.1 `llvmlite` 构建失败（Whisper 安装阶段）

现象：

- `Building wheel for llvmlite ... error`
- `Could not find LLVMConfig.cmake`

原因：

- pip 触发 `llvmlite` 源码编译，缺失 LLVM 开发配置。

修复：

```bash
conda install -c conda-forge numba llvmlite -y
python -m pip install -U openai-whisper --no-build-isolation
```

### 3.2 NumPy 2.x 与 Torch 兼容警告

现象：

- `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x`
- Whisper 可启动但存在潜在崩溃风险。

修复：

```bash
python -m pip install "numpy<2"
# 或
conda install "numpy<2" -y
```

最终确认：

- `numpy==1.26.4`
- `torch==2.2.2`

### 3.3 ImageMagick `montage` 字体错误

现象：

- `montage: unable to read font ...`

修复：

```bash
/opt/homebrew/bin/magick montage frames/*.jpg \
  -font Helvetica \
  -thumbnail 320x180 \
  -geometry +8+8 \
  contact_sheet.jpg
```

## 4. 路径确认（最终可用）

```bash
which python   # /Users/hyq/opt/anaconda3/envs/yt_pdf/bin/python
which whisper  # /Users/hyq/opt/anaconda3/envs/yt_pdf/bin/whisper
which yt-dlp   # /Users/hyq/opt/anaconda3/envs/yt_pdf/bin/yt-dlp
which ffmpeg   # /Users/hyq/opt/anaconda3/envs/yt_pdf/bin/ffmpeg
which magick   # /opt/homebrew/bin/magick
```

## 5. 环境变量配置

项目根目录 `.env`（由 `.env.example` 拷贝）：

```bash
TEXT_BASE_URL=https://api.deepseek.com
TEXT_API_KEY=...
TEXT_MODEL=deepseek-v4-flash
TEXT_STRONG_MODEL=deepseek-v4-pro

VISION_BASE_URL=https://api.moonshot.cn/v1
VISION_API_KEY=...
VISION_MODEL=kimi-k2.6

WHISPER_MODEL=small
WHISPER_LANGUAGE=
```

中英混合转写建议 `WHISPER_LANGUAGE=` 留空，启用自动语言识别。

## 6. 运行健康检查

```bash
/Users/hyq/opt/anaconda3/envs/yt_pdf/bin/yt-dlp --version
/Users/hyq/opt/anaconda3/envs/yt_pdf/bin/ffmpeg -version
/opt/homebrew/bin/magick -version
/Users/hyq/opt/anaconda3/envs/yt_pdf/bin/whisper --help
/Users/hyq/opt/anaconda3/envs/yt_pdf/bin/python -c "import numpy, torch, openai, dotenv; print(numpy.__version__, torch.__version__)"
```

## 7. 当前结论

环境已可用于短视频端到端测试，包含：

- 下载、转写、抽帧、拼图、模型调用、LaTeX 编译。
