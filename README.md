# SKILLS

个人 Agent Skills 集合仓库,兼容开放 Agent Skills 生态([agentskills.io](https://agentskills.io) 规范)。

每个子目录包含一个技能,以 `SKILL.md` 描述其名称与用途,可被 Claude Code、Codex、OpenCode、pi 等主流 AI 编程 agent 识别和加载。

## 目录结构

```
SKILLS/
├── README.md
└── skills/
    ├── find-skills/         # 技能发现助手:帮你搜索并安装其他技能
    ├── content-summary/     # 文档/字幕/视频总结,自带提取脚本
    ├── code-analysis-docs/  # 代码分析→技术文档,自带输出模板
    ├── grill/               # 连环拷问打磨方案,文档按需生成
    ├── create-skill/        # 创建与打磨技能的元技能
    ├── code-review/         # 按语言细分的代码审查,台账沉淀已确认问题
    └── resume-craft/        # 简历打磨:JD 定制+ATS 检查+bullet 量化,显式调用
        └── SKILL.md
```

## 技能列表

| 技能 | 说明 |
| --- | --- |
| [find-skills](skills/find-skills/) | 当你问"有没有能做 X 的 skill"时,自动帮你搜索开放的技能生态并给出安装方式 |
| [content-summary](skills/content-summary/) | 文档与字幕总结:PDF/DOCX/MD + SRT/VTT/ASS/LRC/JSON 字幕 + YouTube/B站链接(字幕优先,无字幕拆帧视觉兜底) + 对话粘贴转录,自带零依赖清洗/拆帧脚本,产出带时间戳和转写修正表的结构化摘要 |
| [code-analysis-docs](skills/code-analysis-docs/) | 代码分析输出技术文档:五阶段流程(侦察→架构深潜→质量评估→基建→成文),证据驱动、引用真实文件路径、置信度追踪,附架构报告/README/API 参考/ADR 产出模板 |
| [grill](skills/grill/) | 连环拷问打磨方案/设计:设计树建模 + 分轮追问(每轮给推荐答案),事实自己查、决策问用户;默认不产出文档,仅在明确要求时才写词汇表(CONTEXT.md)与 ADR |
| [create-skill](skills/create-skill/) | 创建与打磨技能的元技能:采集意图→起草 SKILL.md(frontmatter/openai.yaml/渐进式披露)→测试触发→迭代收尾,内置本仓库全部规范 |
| [code-review](skills/code-review/) | 按语言细分的代码审查:自动识别文件类型加载对应语言清单(Python/TS/Go/C-C++/Java/Rust/通用),可借助 ctags/joern 等代码图谱工具;经用户确认的问题写入持久台账并按模式合并去重,高频模式后续优先复查 |
| [resume-craft](skills/resume-craft/) | 简历打磨(显式调用):以主简历为事实源,五阶段流程(素材盘点→JD 关键词匹配评分→定制决策→bullet 量化改写→ATS 检查),内置 X-Y-Z/STAR 量化框架与技术岗结构规范,产出 HTML→PDF(已验证中文管线)与面试用修改说明 |

## 安装方式

### pi

```bash
pi install git:github.com/LinFangYu123/SKILLS
```

### Claude Code / Codex / Cursor 等(通过 skills CLI)

```bash
npx skills add LinFangYu123/SKILLS
```

### 手动安装

把 `skills/<技能名>/` 复制(或 symlink)到对应 agent 的技能目录,例如:

```bash
# pi 全局技能目录
cp -r skills/find-skills ~/.pi/agent/skills/

# Claude Code
cp -r skills/find-skills ~/.claude/skills/
```


