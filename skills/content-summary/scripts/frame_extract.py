#!/usr/bin/env python3
"""
frame_extract.py — 视频拆帧 + 帧号→时间戳清单（依赖 ffmpeg/ffprobe，无第三方 Python 包）

用途: 无字幕视频走视觉路径时, 把视频拆成关键帧图片供 AI 视觉分批分析;
     产出 frames_manifest.tsv 保证每个帧号都能引用回视频时间点。

用法:
  python3 frame_extract.py video.mp4 -o ./frames              # fps 按视频时长自动分档
  python3 frame_extract.py video.mp4 -o ./frames --fps 0.5    # 指定抽帧率
  python3 video.mp4 -o ./frames --scene 0.3                   # 场景切换检测抽帧(推荐PPT/录屏)
  python3 frame_extract.py video.mp4 -o ./frames --start 60 --end 180   # 只拆某个时间段

抽帧策略选择:
  --fps   均匀采样, 帧号与时间戳一一对应((N-1)/fps), 适合口播/长镜头
  --scene 只在画面剧变时出帧, 适合 PPT/屏幕录制/教程, 帧数少而信息密度高
  二者互斥; 都不给时按视频时长自动选 fps 档: <10min→1fps, <30min→0.5fps, 其余→0.2fps
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def die(msg: str, code: int = 1):
    sys.stderr.write(f"[!] {msg}\n")
    sys.exit(code)


def probe_duration(video: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(video)],
        capture_output=True, text=True)
    if r.returncode != 0:
        die(f"ffprobe 失败: {r.stderr.strip()[-300:]}")
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        die("ffprobe 未返回有效时长")
        return 0.0  # unreachable, 让 die 的 NoReturn 显式化


def auto_fps(duration: float) -> float:
    if duration < 600:
        return 1.0
    if duration < 1800:
        return 0.5
    return 0.2


def fmt_ts(sec: float) -> str:
    sec = int(sec)  # 截断: 时间戳含义是"该帧不早于", 避免 round 半偶舍入的跳变
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def run_ffmpeg(args: list) -> subprocess.CompletedProcess:
    r = subprocess.run(["ffmpeg", "-y", *args], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        die("ffmpeg 抽帧失败 (检查视频路径/时间范围)")
    return r


def parse_clock(t: str) -> float:
    """'5' / '1:30' / '0:1:30' -> 秒"""
    if not t:
        return 0.0
    p = [float(x) for x in t.split(":")]
    if len(p) == 3:
        return p[0] * 3600 + p[1] * 60 + p[2]
    if len(p) == 2:
        return p[0] * 60 + p[1]
    return p[0]


def extract_fps(video: Path, out_dir: Path, fps: float, ss: str, to: str):
    out_pat = out_dir / "frame_%04d.jpg"
    cmd = ["-i", str(video)]
    if ss:
        cmd += ["-ss", ss]
    if to:
        cmd += ["-to", to]
    cmd += ["-vf", f"fps={fps}", "-q:v", "2", str(out_pat)]
    run_ffmpeg(cmd)
    frames = sorted(out_dir.glob("frame_*.jpg"))
    # fps 模式: 第 N 帧(1-based) ≈ 起点 + (N-1)/fps + 半帧中点
    start = parse_clock(ss)
    return [(f, start + (i + 0.5) / fps) for i, f in enumerate(frames)]


def extract_scene(video: Path, out_dir: Path, thresh: float, ss: str, to: str):
    # metadata=print 把每个被选中帧的 pts_time 写进清单, 保住帧→时间映射
    raw = out_dir / "_scene_meta.txt"
    vf = f"select='gt(scene,{thresh})',metadata=print:file={raw}"
    cmd = ["-i", str(video)]
    if ss:
        cmd += ["-ss", ss]
    if to:
        cmd += ["-to", to]
    cmd += ["-vf", vf, "-vsync", "vfr", "-q:v", "2", str(out_dir / "frame_%04d.jpg")]
    run_ffmpeg(cmd)
    frames = sorted(out_dir.glob("frame_*.jpg"))
    times = []
    if raw.exists():
        for line in raw.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r"pts_time:([\d.]+)", line)
            if m:
                times.append(float(m.group(1)))
        raw.unlink()
    start = parse_clock(ss)
    # 场景切换发生在"上一帧→本帧"之间, 时间戳取 pts_time
    return [(f, start + (times[i] if i < len(times) else 0.0))
            for i, f in enumerate(frames)]


def main():
    ap = argparse.ArgumentParser(description="视频拆帧 + 时间戳清单 (ffmpeg 前端)")
    ap.add_argument("video", help="本地视频文件 (先自行用 yt-dlp 下载)")
    ap.add_argument("-o", "--output", required=True, help="帧输出目录")
    ap.add_argument("--fps", type=float, help="每秒抽帧数(默认按时长自动分档)")
    ap.add_argument("--scene", type=float, metavar="T",
                    help="场景切换阈值(0-1), 如 0.3; 与 --fps 互斥, 推荐 PPT/录屏")
    ap.add_argument("--start", help="起始时间 mm:ss 或 hh:mm:ss")
    ap.add_argument("--end", help="结束时间 mm:ss 或 hh:mm:ss")
    args = ap.parse_args()

    video = Path(args.video)
    if not video.exists():
        die(f"视频不存在: {video} (需先用 yt-dlp 下载)")
    for tool in ("ffmpeg", "ffprobe"):
        if subprocess.run(["which", tool], capture_output=True).returncode:
            die(f"缺少 {tool}")

    duration = probe_duration(video)
    mode = "scene" if args.scene else "fps"
    fps_val = args.fps if args.fps else None
    if not args.scene and fps_val is None:
        fps_val = auto_fps(duration)
        sys.stderr.write(f"[auto] 时长 {fmt_ts(duration)} → fps={fps_val}\n")

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    if list(out_dir.glob("frame_*.jpg")):
        die(f"{out_dir} 已有帧文件, 换个目录或先清空")

    ss = args.start or ""
    fps_arg = fps_val if fps_val is not None else 1.0
    frames = (extract_scene(video, out_dir, args.scene, ss, args.end) if args.scene
              else extract_fps(video, out_dir, fps_arg, ss, args.end))

    manifest = out_dir / "frames_manifest.tsv"
    with manifest.open("w", encoding="utf-8") as fh:
        fh.write("frame\ttime\tmmss\n")
        for f, t in frames:
            fh.write(f"{f.name}\t{t:.1f}\t{fmt_ts(t)}\n")

    sys.stderr.write(f"[ok] {len(frames)} 帧 → {out_dir}/frame_*.jpg\n"
                     f"[ok] 时间戳清单: {manifest}\n")
    if len(frames) > 120:
        sys.stderr.write("[warn] 帧数>120: 视觉分析按每批≤30帧分批, 或提高 --scene 阈值/降低 fps\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
