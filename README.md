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
    └── create-skill/        # 创建与打磨技能的元技能
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

## 添加新技能

1. 在 `skills/` 下新建目录,目录名即技能名
2. 编写 `SKILL.md`,必须包含 YAML frontmatter(`name` 与 `description`)
3. 提交并推送,agent 启动时会自动发现

```markdown
---
name: my-skill
description: 一句话描述触发场景,越具体越好
---

# My Skill

使用说明、步骤、脚本路径等。
```

### 调用控制与 OpenAI 兼容层

#### `disable-model-invocation: true`（SKILL.md frontmatter）

默认情况下,agent 会读取所有技能的 `description`,对话中判断相关就**自动加载**
（隐式触发）。如果技能不希望被自动触发,只能由用户显式调用（例如像 grill
这种会接管整个对话节奏的技能）,在 frontmatter 加一行:

```markdown
---
name: my-skill
description: 一句话描述触发场景
disable-model-invocation: true   ← 加这行,pif/Claude Code 等会禁止模型自动触发
---
```

本仓库中的 [grill](skills/grill/) 就使用了该字段;其余技能均依赖自动触发,不加。

#### `agents/openai.yaml`（Codex 兼容元数据）

OpenAI 系平台（Codex CLI 等）不读 SKILL.md 的通用字段,需要自己的专属配置。
建议每个技能都提供 `agents/openai.yaml`,为 Codex 提供界面显示与调用策略:

```yaml
# skills/my-skill/agents/openai.yaml
interface:
  display_name: "My Skill"                     # 界面上显示的名称
  short_description: "One-line description"    # 一句话简介
policy:
  allow_implicit_invocation: false             # 仅当 SKILL.md 里写了
                                               # disable-model-invocation: true 时才加,
                                               # 与之呼应;允许自动触发的技能省略整个 policy 段
```

- 其他 agent（pi、Claude Code、OpenCode 等）读到 `agents/` 目录会直接忽略,不影响使用
- 本仓库四个技能均已提供该文件,可作参考

### 目录结构参考

```
skills/my-skill/
├── SKILL.md              # 必需:通用规范(所有 agent 读取)
├── agents/
│   └── openai.yaml       # 推荐:Codex 专属元数据
├── references/           # 可选:参考资料、模板
└── scripts/              # 可选:配套脚本
```
