# SKILLS

个人 Agent Skills 集合仓库,兼容开放 Agent Skills 生态([agentskills.io](https://agentskills.io) 规范)。

每个子目录包含一个技能,以 `SKILL.md` 描述其名称与用途,可被 Claude Code、Codex、OpenCode、pi 等主流 AI 编程 agent 识别和加载。

## 目录结构

```
SKILLS/
├── README.md
└── skills/
    └── find-skills/       # 技能发现助手:帮你搜索并安装其他技能
        └── SKILL.md
```

## 技能列表

| 技能 | 来源 | 说明 |
| --- | --- | --- |
| [find-skills](skills/find-skills/) | [vercel-labs/skills](https://github.com/vercel-labs/skills) | 当你问"有没有能做 X 的 skill"时,自动帮你搜索开放的技能生态并给出安装方式 |

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
