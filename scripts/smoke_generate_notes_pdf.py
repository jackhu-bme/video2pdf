#!/usr/bin/env python3
"""
Smoke test pipeline for short YouTube video:
1) read .env
2) call Kimi vision on key frames
3) call DeepSeek to build structured notes JSON
4) render notes.tex
5) run xelatex twice to produce notes.pdf
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


def tex_escape(text: str | None) -> str:
    if text is None:
        return ""
    s = str(text)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(c, c) for c in s)


def data_url(image_path: Path) -> str:
    mime = "image/jpeg" if image_path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def extract_json(text: str) -> dict:
    candidate = text.strip()
    block = re.search(r"```(?:json)?\s*(.*?)```", candidate, re.S)
    if block:
        candidate = block.group(1).strip()
    return json.loads(candidate)


def mmss_to_seconds(value: str) -> int:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format {value}, expected MM:SS")
    mm = int(parts[0])
    ss = int(parts[1])
    if ss < 0 or ss >= 60 or mm < 0:
        raise ValueError(f"Invalid MM:SS value {value}")
    return mm * 60 + ss


def seconds_to_label(sec: int) -> str:
    mm = sec // 60
    ss = sec % 60
    return f"{mm:02d}:{ss:02d}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a smoke-test notes PDF from local assets.")
    parser.add_argument("--workdir", default=".", help="Working directory containing audio/video/subtitles/frames")
    parser.add_argument("--env", default="../../.env", help="Path to .env relative to workdir")
    parser.add_argument(
        "--frames",
        default="01:00,02:30,04:30",
        help="Comma-separated MM:SS timestamps mapped to frame_XXX.jpg where XXX starts at 1 every 30s",
    )
    parser.add_argument("--frame-interval", type=int, default=30, help="Seconds per extracted frame (default 30)")
    parser.add_argument("--text-model", default="", help="Override TEXT model")
    parser.add_argument("--vision-model", default="", help="Override VISION model")
    parser.add_argument("--xelatex", default="/Library/TeX/texbin/xelatex", help="Path to xelatex")
    parser.add_argument("--magick", default="/opt/homebrew/bin/magick", help="Path to ImageMagick magick")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.workdir).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Workdir not found: {root}")

    env_path = (root / args.env).resolve()
    if not env_path.exists():
        raise FileNotFoundError(f".env not found at: {env_path}")

    load_dotenv(env_path)

    required = [
        "TEXT_API_KEY",
        "TEXT_BASE_URL",
        "VISION_API_KEY",
        "VISION_BASE_URL",
    ]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    text_model = args.text_model or os.environ.get("TEXT_STRONG_MODEL") or os.environ.get("TEXT_MODEL", "deepseek-v4-flash")
    vision_model = args.vision_model or os.environ.get("VISION_MODEL", "kimi-k2.6")

    info_file = next(root.glob("*.info.json"), None)
    if info_file is None:
        raise FileNotFoundError("No *.info.json found in workdir")
    info = json.loads(info_file.read_text())

    srt_path = root / "subtitles" / "audio.srt"
    if not srt_path.exists():
        raise FileNotFoundError(f"Subtitle not found: {srt_path}")
    srt_text = srt_path.read_text(errors="ignore")[:12000]

    text_client = OpenAI(api_key=os.environ["TEXT_API_KEY"], base_url=os.environ["TEXT_BASE_URL"])
    vision_client = OpenAI(api_key=os.environ["VISION_API_KEY"], base_url=os.environ["VISION_BASE_URL"])

    frame_times = [x.strip() for x in args.frames.split(",") if x.strip()]
    frame_pairs: list[tuple[str, Path]] = []
    for t in frame_times:
        sec = mmss_to_seconds(t)
        idx = sec // args.frame_interval + 1
        frame_file = root / "frames" / f"frame_{idx:03d}.jpg"
        if not frame_file.exists():
            raise FileNotFoundError(f"Frame missing for {t}: {frame_file}")
        frame_pairs.append((seconds_to_label(sec), frame_file))

    vision_notes_parts: list[str] = []
    for label, frame_file in frame_pairs:
        response = vision_client.chat.completions.create(
            model=vision_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "请用中文描述这张视频截图。要求："
                                "1. 说明画面中正在发生什么；"
                                "2. 判断它是否适合作为视频总结配图；"
                                "3. 如果适合，给出一句图注。"
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url(frame_file)}},
                    ],
                }
            ],
        )
        content = response.choices[0].message.content.strip()
        vision_notes_parts.append(f"## {label} {frame_file.name}\n\n{content}\n")

    vision_notes = "\n".join(vision_notes_parts)
    (root / "vision_notes.md").write_text(vision_notes)

    prompt = f"""
你要为一个短视频生成 PDF 笔记内容。
请根据 metadata、Whisper SRT 字幕、Kimi 图像理解结果，输出严格 JSON，不要 Markdown fence。

JSON schema:
{{
  "title": "标题",
  "overview": "100-200字概述",
  "timeline": [
    {{"time": "00:00-00:30", "text": "这一段发生了什么"}}
  ],
  "visual_choices": [
    {{"image": "frames/frame_003.jpg", "caption": "图注", "reason": "为什么适合或不适合"}}
  ],
  "highlights": ["看点1", "看点2", "看点3"],
  "takeaways": ["结论1", "结论2"]
}}

metadata:
{json.dumps({
    'title': info.get('title'),
    'duration': info.get('duration'),
    'webpage_url': info.get('webpage_url'),
    'uploader': info.get('uploader'),
    'upload_date': info.get('upload_date')
}, ensure_ascii=False, indent=2)}

SRT:
{srt_text}

Kimi 图像理解:
{vision_notes}
"""

    text_response = text_client.chat.completions.create(
        model=text_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )

    raw = text_response.choices[0].message.content
    (root / "deepseek_raw.txt").write_text(raw)
    notes = extract_json(raw)
    (root / "notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=2))

    cover_src = next(root.glob("*.webp"), None) or next(root.glob("*.jpg"), None)
    cover_out = root / "cover.jpg"
    if cover_src is not None and cover_src.suffix.lower() == ".webp":
        subprocess.run([args.magick, str(cover_src), str(cover_out)], check=True)
    elif cover_src is not None:
        cover_out.write_bytes(cover_src.read_bytes())

    timeline_tex = ""
    for row in notes.get("timeline", []):
        timeline_tex += rf"\subsection*{{{tex_escape(row.get('time', ''))}}}" + "\n"
        timeline_tex += tex_escape(row.get("text", "")) + "\n\n"

    visual_tex = ""
    visual_choices = notes.get("visual_choices", [])
    for i, (label, frame_file) in enumerate(frame_pairs):
        caption = ""
        if i < len(visual_choices):
            caption = visual_choices[i].get("caption", "")
        if not caption:
            caption = f"视频关键帧 {label}"
        visual_tex += rf"""
\begin{{figure}}[H]
\centering
\includegraphics[width=0.92\textwidth]{{frames/{frame_file.name}}}
\caption{{{tex_escape(caption)}\protect\footnotemark}}
\end{{figure}}
\footnotetext{{视频抽帧位置约为：{tex_escape(label)}。}}
"""

    def itemize(items: list[str]) -> str:
        if not items:
            return ""
        return "\n".join([rf"\item {tex_escape(x)}" for x in items])

    cover_line = ""
    if cover_out.exists():
        cover_line = "\\includegraphics[width=0.82\\textwidth,height=0.38\\textheight,keepaspectratio]{cover.jpg}"

    tex = rf"""
\documentclass[a4paper]{{article}}
\usepackage[fontset=fandol]{{ctex}}
\usepackage{{graphicx}}
\usepackage[margin=2.5cm]{{geometry}}
\usepackage[most]{{tcolorbox}}
\usepackage{{hyperref}}
\usepackage{{float}}
\usepackage{{enumitem}}
\hypersetup{{colorlinks=true, linkcolor=blue, urlcolor=blue}}

\title{{{tex_escape(notes.get('title') or info.get('title', 'Untitled'))}}}
\author{{video2pdf smoke test}}
\date{{\today}}

\begin{{document}}
\maketitle

\begin{{center}}
{cover_line}
\end{{center}}

\begin{{tcolorbox}}[colback=black!2!white, colframe=black!50, sharp corners]
\textbf{{视频标题}}：{tex_escape(info.get('title'))}\par
\textbf{{频道}}：{tex_escape(info.get('uploader'))}\par
\textbf{{时长}}：{tex_escape(info.get('duration'))} 秒\par
\textbf{{链接}}：\href{{{info.get('webpage_url')}}}{{{tex_escape(info.get('webpage_url'))}}}
\end{{tcolorbox}}

\tableofcontents
\newpage

\section{{视频概述}}
{tex_escape(notes.get('overview', ''))}

\section{{剧情与内容推进}}
{timeline_tex}

\section{{关键画面}}
{visual_tex}

\section{{主要看点}}
\begin{{itemize}}[leftmargin=2em]
{itemize(notes.get('highlights', []))}
\end{{itemize}}

\section{{总结}}
\begin{{itemize}}[leftmargin=2em]
{itemize(notes.get('takeaways', []))}
\end{{itemize}}

\end{{document}}
"""

    (root / "notes.tex").write_text(tex)

    for _ in range(2):
        subprocess.run([args.xelatex, "-interaction=nonstopmode", "notes.tex"], cwd=root, check=True)

    print("DONE")
    print(root / "notes.pdf")


if __name__ == "__main__":
    main()
