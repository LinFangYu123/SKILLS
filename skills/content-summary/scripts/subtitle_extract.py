#!/usr/bin/env python3
"""
subtitle_extract.py — 字幕文件清洗与文本提取(零第三方依赖)

支持格式: SRT / WebVTT / ASS·SSA / LRC / B站·通用JSON 字幕 / 纯文本(自动嗅探)
输出:     可读纯文本(按静音间隔分段) 或 带时间戳的行 或 结构化 JSON

用法:
  python3 subtitle_extract.py input.srt                  # 纯文本, 30s 间隔分段
  python3 subtitle_extract.py input.ass --format stamps  # [mm:ss] 文本
  python3 subtitle_extract.py video.vtt --min-gap 45 --stats
  python3 subtitle_extract.py bilibili.json --lang zh    # 双语字幕只留中文行

设计说明:
  - 逐条拼接时中文条目间不加空格(中文无词间空格), 西文条目间加空格,
    避免断词被粘连。
  - 默认丢弃噪音条目: (音乐) / [Music] / ♪ / 纯符号等。
  - 分段依据: 上一条结束时间到下一条开始时间的静音间隔 > --min-gap。
"""

import argparse
import json
import re
import sys
from pathlib import Path

TS_RE = re.compile(r"(?:\d{1,2}:)?\d{1,2}:\d{1,2}[,.]\d{1,3}")

TIME_TAG_RE = re.compile(r"<(?:\d{1,2}:)?\d{1,2}:\d{1,2}[.,]\d{1,3}>")

LRC_RE = re.compile(r"^\[(\d{1,2}):(\d{2})(?:[.:](\d{1,3}))?\]\s*(.*)$")

NOISE_TAG_RE = re.compile(
    r"[\(\[]\s*(music|applause|audio|silence|inaudible|background music"
    r"|音乐|音效|掌声|静音|无内容|背景音乐)\s*[\)\]]"
    r"|♪+",
    re.IGNORECASE,
)

SYMBOL_ONLY_RE = re.compile(r"^[\s\-\_=*·・]+$")

HAS_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

TAG_STRIP_RE = re.compile(r"<[^>]+>|\{[^}]*\}")


def ts_to_seconds(s: str) -> float:
    """'01:02:03,456' / '1:02.345' / '02.5' -> 秒"""
    s = s.strip().replace(",", ".")
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h, m, sec = parts
        elif len(parts) == 2:
            h, m, sec = 0, parts[0], parts[1]
        else:
            h, m, sec = 0, 0, parts[0]
        return int(h) * 3600 + int(m) * 60 + float(sec)
    except ValueError:
        return 0.0


def parse_time_range(line: str):
    """SRT/VTT 时间轴行: '00:01:02,345 --> 00:01:05,000' -> (start, end)"""
    if "-->" not in line:
        return None
    left, _, right = line.partition("-->")
    m_start, m_end = TS_RE.search(left), TS_RE.search(right)
    if not (m_start and m_end):
        return None
    return ts_to_seconds(m_start.group(0)), ts_to_seconds(m_end.group(0))


def clean_text(text: str) -> str:
    text = TIME_TAG_RE.sub("", text)
    text = TAG_STRIP_RE.sub("", text)
    text = NOISE_TAG_RE.sub("", text)
    text = text.replace("\\N", " ").replace("\\n", " ").replace("\\h", " ")
    return re.sub(r"\s+", " ", text).strip()


def is_noise(text: str) -> bool:
    """清洗后仅剩符号/空白 -> 噪音条目"""
    return not text.strip() or bool(SYMBOL_ONLY_RE.match(text))


def detect_format(path: Path, head: str) -> str:
    ext = path.suffix.lower()
    if ext in (".ass", ".ssa"):
        return "ass"
    if ext == ".lrc":
        return "lrc"
    if ext == ".json":
        return "json"
    if ext == ".vtt" or head.lstrip().startswith("WEBVTT"):
        return "vtt"
    if "[Script Info]" in head or "Format: Layer" in head:
        return "ass"
    if re.search(r"^\[\d{1,2}:\d{2}", head, re.MULTILINE):
        return "lrc"
    if "-->" in head:
        return "srt"
    if head.lstrip()[:1] in ("{", "["):
        return "json"
    return "plain"


def parse_srt_vtt(text: str):
    """返回 [(start, end, text)]"""
    entries = []
    cur = None  # [start, end, lines[]]
    for line in text.splitlines():
        rng = parse_time_range(line)
        if rng:
            if cur and cur[2]:
                entries.append(cur)
            cur = [rng[0], rng[1], []]
            continue
        if cur is not None:
            body = clean_text(line)
            if body and not re.fullmatch(r"\d+", body):  # 跳过序号行
                cur[2].append(body)
    if cur and cur[2]:
        entries.append(cur)
    return [(s, e, " ".join(t)) for s, e, t in entries
            if not is_noise(" ".join(t))]


def parse_ass(text: str):
    entries = []
    # 从 [Events] 的 Format 行确定 Text 是第几列(通常第10列)
    n_before = 9
    ev_pos = text.find("[Events]")
    fm = re.search(r"^Format:\s*(.+)$", text[ev_pos:] if ev_pos >= 0 else text, re.M)
    if fm:
        cols = [c.strip().lower() for c in fm.group(1).split(",")]
        if "text" in cols:
            n_before = cols.index("text")
    for line in text.splitlines():
        line = line.strip()
        if not line.lower().startswith("dialogue:"):
            continue
        rest = line[len("dialogue:"):].strip()
        fields = rest.split(",", n_before)
        if len(fields) <= n_before:
            continue
        body = clean_text(fields[-1])
        start = ts_to_seconds(fields[1]) if len(fields) > 2 else 0.0
        end = ts_to_seconds(fields[2]) if len(fields) > 2 else start
        if body and not is_noise(body):
            entries.append((start, end, body))
    return entries


def parse_lrc(text: str):
    entries = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = LRC_RE.match(line.strip())
        if not m:
            continue
        start = int(m.group(1)) * 60 + int(m.group(2)) + float("0." + (m.group(3) or "0"))
        body = clean_text(m.group(4))
        if body and not is_noise(body):
            entries.append((start, start, body))
    # 结束时间 = 下一条开始时间
    for i in range(len(entries) - 1):
        entries[i] = (entries[i][0], entries[i + 1][0], entries[i][2])
    if entries:
        s, _, t = entries[-1]
        entries[-1] = (s, s + 5, t)
    return entries


def parse_json_subs(text: str):
    """B站 {events:[{tStartMs,durationMs,segs:[{utf8}]}]} / 通用 [{start,end,text}]"""
    data = json.loads(text)
    entries = []
    events = []
    if isinstance(data, dict):
        events = data.get("events") or data.get("subtitle") or data.get("captions") or []
    elif isinstance(data, list):
        events = data
    for ev in events:
        start = end = 0.0
        body = ""
        if "segs" in ev:  # B站
            start = ev.get("tStartMs", 0) / 1000.0
            end = start + ev.get("durationMs", 0) / 1000.0
            body = "".join(clean_str(s.get("utf8") or s.get("text") or "")
                           for s in ev["segs"])
        else:
            for k_s in ("start", "tStartMs", "offset", "offset_ms", "begin"):
                if k_s in ev:
                    v = float(ev[k_s])
                    start = v / 1000.0 if v > 1e7 else v
                    break
            for k_e in ("end", "tEndMs", "duration", "duration_ms"):
                if k_e in ev:
                    v = float(ev[k_e])
                    end = start + (v / 1000.0 if v > 1e7 else v) if k_e.startswith("dur") else (v / 1000.0 if v > 1e7 else v)
                    break
            body = clean_str(ev.get("content") or ev.get("text") or ev.get("utf8") or "")
        if body and not is_noise(body):
            entries.append((start, end or start, body))
    return entries


def clean_str(x):
    return clean_text(str(x))


def dedupe_rolling(entries):
    """YouTube 自动生成字幕是累积滚动的(每条 cue 包含前文), 直接拼接会重复数遍。
    规则: 新条目 == 上一条 -> 丢弃; 新条目以上一条开头(累积形态) -> 原位合并为最新全文;
    上一条以新条目开头(回缩噪音) -> 丢弃新条目。仅处理相邻条目, 保守合并。
    """
    out = []
    for s, e, t in entries:
        if out:
            ps, pe, pt = out[-1]
            if t == pt or pt.startswith(t):
                continue
            if t.startswith(pt):
                out[-1] = (ps, max(pe, e), t)
                continue
        out.append((s, e, t))
    return out


def fmt_ts(sec: float, mode: str) -> str:
    sec = int(round(sec))
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    if mode == "sec":
        return f"[{sec}s]"
    return f"[{h}:{m:02d}:{s:02d}]" if h else f"[{m:02d}:{s:02d}]"


def emit(entries, min_gap, ts_prefix):
    """按静音间隔分段输出连贯文本。"""
    paragraphs = []
    buf, buf_start = [], None
    prev_end = None
    for start, end, text in entries:
        if prev_end is not None and (start - prev_end) > min_gap and buf:
            paragraphs.append((buf_start, buf))
            buf, buf_start = [], None
        if not buf:
            buf_start = start
        buf.append(text)
        prev_end = max(prev_end or 0.0, end)
    if buf:
        paragraphs.append((buf_start, buf))

    blocks = []
    for pstart, lines in paragraphs:
        merged = lines[0]
        for nxt in lines[1:]:
            sep = "" if (HAS_CJK_RE.search(merged[-1]) or HAS_CJK_RE.search(nxt[0])) else " "
            merged += sep + nxt
        prefix = fmt_ts(pstart, ts_prefix) + " " if ts_prefix != "none" else ""
        blocks.append(prefix + merged)
    return "\n\n".join(blocks)


def main():
    ap = argparse.ArgumentParser(description="字幕文件 -> 清洗后的可读文本")
    ap.add_argument("file", help="字幕文件路径 (srt/vtt/ass/lrc/json/txt)")
    ap.add_argument("--format", choices=["text", "stamps", "json"], default="text",
                    help="text=分段纯文本(默认) stamps=每行带时间戳 json=结构化条目")
    ap.add_argument("--min-gap", type=float, default=30.0,
                    help="text 模式分段静音阈值(秒), 默认30")
    ap.add_argument("--lang", choices=["zh", "all"], default="all",
                    help="zh=只保留含中文的条目(双语字幕去英文行)")
    ap.add_argument("--dedupe", action="store_true",
                    help="合并 YouTube 自动生成字幕的累积滚动重复(相邻条目前后缀包含)")
    ap.add_argument("--stats", action="store_true", help="输出统计信息到 stderr")
    ap.add_argument("-o", "--output", help="写入文件而非 stdout")
    args = ap.parse_args()

    raw = Path(args.file).read_text(encoding="utf-8", errors="replace")
    fmt = detect_format(Path(args.file), raw[:2000])

    if fmt in ("srt", "vtt"):
        entries = parse_srt_vtt(raw)
    elif fmt == "ass":
        entries = parse_ass(raw)
    elif fmt == "lrc":
        entries = parse_lrc(raw)
    elif fmt == "json":
        entries = parse_json_subs(raw)
    else:
        sys.stderr.write(f"[!] 无法识别字幕格式({fmt}), 按纯文本透传输出\n")
        print(raw)
        return 1

    if args.dedupe:
        before = len(entries)
        entries = dedupe_rolling(entries)
        sys.stderr.write(f"[dedupe] {before} -> {len(entries)} 条\n")

    if args.lang == "zh":
        entries = [(s, e, t) for s, e, t in entries if HAS_CJK_RE.search(t)]

    if args.stats:
        duration = (entries[-1][1] - entries[0][0]) if entries else 0
        chars = sum(len(t) for _, _, t in entries)
        sys.stderr.write(
            f"[stats] 格式={fmt} 条目={len(entries)} "
            f"时长≈{duration/60:.1f}min 字符={chars}\n")

    if not entries:
        sys.stderr.write("[!] 未提取到任何字幕条目\n")
        return 2

    if args.format == "json":
        out = json.dumps([{"start": round(s, 3), "end": round(e, 3), "text": t}
                          for s, e, t in entries], ensure_ascii=False, indent=1)
    elif args.format == "stamps":
        out = "\n".join(f"{fmt_ts(s, 'auto')} {t}" for s, _, t in entries)
    else:
        out = emit(entries, args.min_gap, ts_prefix="none")

    if args.output:
        Path(args.output).write_text(out + "\n", encoding="utf-8")
        sys.stderr.write(f"[ok] 写入 {args.output} ({len(out)} 字符)\n")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
