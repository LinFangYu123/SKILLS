#!/usr/bin/env python3
"""teach 工作区脚手架：建目录、落共享样式与测验组件、写 PROGRESS.md 骨架。

零依赖，幂等：已存在的文件不动，除非 --force。

用法:
    python3 scaffold_workspace.py --dir . --topic "分布式系统"
    python3 scaffold_workspace.py --dir ./learn-rust --topic "Rust" --lang en --force

退出码: 0 成功 · 1 参数/IO 错误
"""

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"

SUBDIRS = ["lessons", "reference", "learning-records", "mastery", "assets"]
ASSETS = ["style.css", "quiz.js"]

PROGRESS = {
    "zh": """# {topic} 学习进度

<!-- 由 teach 分支 2 / 分支 4 维护。只放聚合数字与当前状态，不要追加会话日志。 -->

## 里程碑

| # | 里程碑（可观察的产出） | 判据 | 检查点 | 状态 |
| --- | --- | --- | --- | --- |
| 1 |  |  |  | ⬜ |

状态：⬜ 未开始 · 🟡 进行中 · ✅ 达成 · ⏸ 搁置

## 熟练度总览

| 主题域 | 已测 | 正确 | 正确率 | 等级 | 明细 |
| --- | --- | --- | --- | --- | --- |
| **合计** | **0** | **0** | **-** | ⬜ | |

等级：🟥 0-39% · 🟨 40-69% · 🟩 70-89% · 🟦 90-100% · ⬜ 未测

## 当前弱项（最多 3 条）

（暂无——基线评估后填写）

## 下一节

（待定）
""",
    "en": """# {topic} — Learning Progress

<!-- Maintained by teach branch 2 / branch 4. Aggregates and current state only; never a session log. -->

## Milestones

| # | Milestone (observable output) | Pass criterion | Checkpoint | Status |
| --- | --- | --- | --- | --- |
| 1 |  |  |  | ⬜ |

Status: ⬜ not started · 🟡 in progress · ✅ met · ⏸ deferred

## Proficiency

| Area | Tested | Correct | Rate | Level | Detail |
| --- | --- | --- | --- | --- | --- |
| **Total** | **0** | **0** | **-** | ⬜ | |

Levels: 🟥 0-39% · 🟨 40-69% · 🟩 70-89% · 🟦 90-100% · ⬜ unmeasured

## Current weak spots (max 3)

(none yet — fill in after the baseline assessment)

## Next lesson

(TBD)
""",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold a teach workspace.")
    ap.add_argument("--dir", default=".", help="工作区目录（默认当前目录）")
    ap.add_argument("--topic", required=True, help="主题名，写进 PROGRESS.md 的标题")
    ap.add_argument("--lang", choices=sorted(PROGRESS), default="zh", help="骨架文案语言（默认 zh）")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 assets / PROGRESS.md")
    args = ap.parse_args()

    root = Path(args.dir).expanduser().resolve()
    if not TEMPLATES.is_dir():
        print(f"错误：找不到模板目录 {TEMPLATES}", file=sys.stderr)
        return 1
    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"错误：无法创建 {root} —— {e}", file=sys.stderr)
        return 1

    made, skipped = [], []

    for d in SUBDIRS:
        (root / d).mkdir(exist_ok=True)
        made.append(f"{d}/")

    for name in ASSETS:
        src, dst = TEMPLATES / name, root / "assets" / name
        if dst.exists() and not args.force:
            skipped.append(f"assets/{name}")
            continue
        shutil.copyfile(src, dst)
        made.append(f"assets/{name}")

    progress = root / "PROGRESS.md"
    if progress.exists() and not args.force:
        skipped.append("PROGRESS.md")
    else:
        progress.write_text(PROGRESS[args.lang].format(topic=args.topic), encoding="utf-8")
        made.append("PROGRESS.md")

    print(f"工作区: {root}")
    if made:
        print("已创建: " + ", ".join(made))
    if skipped:
        print("已存在(未动): " + ", ".join(skipped) + "  —— 需要覆盖加 --force")
    print()
    print("下一步（teach 分支 1）：")
    print(f"  1. 访谈用户，问清「为什么学 {args.topic}」——模糊的使命比没有使命更糟")
    print("  2. 写 MISSION.md（模板见 references/formats.md）")
    print("  3. 出 6-8 道零提示题做基线评估，结果写进 mastery/<area>.md")
    print("  4. 建 RESOURCES.md：3 条以上带注解的高可信来源，或显式写 ## Gaps")
    print("  5. 把里程碑与可测判据填进 PROGRESS.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
