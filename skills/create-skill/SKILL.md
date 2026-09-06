---
name: create-skill
description: Create, edit, or improve agent skills for this repository — capture intent, draft SKILL.md with frontmatter and openai.yaml, structure bundled resources, and iterate via test prompts. Use when the user says 创建技能/新建skill/写个skill/做成技能, asks to turn a workflow into a skill, wants to improve or restructure an existing skill, or mentions SKILL.md, agentskills.io, or the SKILLS repo. Even if they only say "把这个流程固化下来", use this skill.
version: "1.0.0"
---

# Create Skill（创建与打磨技能）

为**本仓库**（agentskills.io 开放规范）创建、修改技能。
核心循环：**采集意图 → 起草 → 测试 → 迭代**，直到用户满意后提交推送。

---

## 第一步：采集意图

动手写之前先弄清楚（前三个问题对话中已有答案的直接提取，缺的才问；
第 4 个**必须询问用户**，不要自行决定）：

1. **做什么**：这个技能要让 agent 能完成什么？
2. **何时触发**：用户会说什么话、在什么场景下需要它？
3. **产出形式**：期望的输出格式是什么？
4. **默认触发还是显式调用**：会不会接管对话节奏？**问用户**：
   「这个技能是希望 agent 在对话中自动触发，还是只能显式调用？
   」（接管式流程如拷问/规划类建议显式；辅助类如分析/总结建议默认触发；
   用户的答案决定是否需要 `disable-model-invocation: true`，见下文）

## 第二步：起草 SKILL.md

### 目录结构

```
skills/<skill-name>/
├── SKILL.md              # 必需:通用规范(所有 agent 读取)
├── agents/
│   └── openai.yaml       # 推荐:Codex 专属元数据(界面显示 + 调用策略)
├── references/           # 可选:参考资料、格式模板
└── scripts/              # 可选:配套脚本(零依赖优先)
```

### Frontmatter 必备字段

```markdown
---
name: <目录名同名>
description: 一句话描述触发场景,越具体越好
version: "1.0.0"
---
```

**description 是唯一的触发机制**——agent 只靠它在对话中决定是否加载本技能。
写作要点：

- 同时包含「做什么」和「何时用」，把所有触发线索放这里，不放正文
- 适当"外向"一点：用户不会总用你预想的措辞。除了精确场景，也覆盖
  邻近说法（中英文触发词都列上，如「总结/精读/summarize」）
- 参考本仓库现有技能的 description 风格

### 可选：禁止自动触发

如果技能会**接管整个对话**（如连环追问、需要多轮确认的流程），
在 frontmatter 加一行，并在 `agents/openai.yaml` 里呼应：

```yaml
# SKILL.md frontmatter
disable-model-invocation: true

# agents/openai.yaml
interface:
  display_name: "<人类可读名称>"
  short_description: "<一句话简介>"
policy:
  allow_implicit_invocation: false   # 仅与上面那行配套时才加 policy 段
```

其余技能省略 `policy` 段（OpenAI 平台默认允许隐式触发），只写 `interface`。
`agents/` 目录对其他 agent 不可见，加了对 pi、Claude Code 等无副作用。

### 正文写作规范

- **渐进式披露**：SKILL.md 控制在 ~500 行内。装不下的内容放
  `references/`，在正文里**明确指出何时去读哪个文件**（如
  「格式见 [ADR-FORMAT.md](./references/ADR-FORMAT.md)」）
- **多领域分文件**：技能支持多个框架/场景时，按变体拆 reference
  （`references/aws.md`、`references/gcp.md`…），agent 只读相关的那份
- **祈使句**、解释**为什么**而不是堆 MUST；想写 ALWAYS/NEVER 时，
  先想想能不能把理由讲清楚来替代
- **可复用的重复劳动进 scripts/**：测试中如果每轮都要手写同样的
  辅助脚本，就固化一份放进 `scripts/`
- 大参考文件（>300 行）开头加目录
- 正文用中文，遵循本仓库现有风格；开头保留一行「参考设计：xxx」注明
  借鉴来源

## 第三步：测试

写完草稿后，构造 **2-3 个真实的测试提示词**（用户实际会说的话，含
具体细节而非抽象指令），和用户确认后逐个验证：

- 给 agent 装上该技能（symlink 或 cp 到技能目录），运行测试提示
- 观察三件事：**是否触发**（description 是否把该接的对话接住了）、
  **执行质量**（产出是否符合预期格式）、**是否误触发**（不该触发的
  对话有没有被错误拉进来）
- 触发不理想的，回去改 description——这是最高频的迭代点

不需要搭正式评测框架：人工检查产出 + 用户反馈即可，别让流程重过产出。

## 第四步：迭代与收尾

根据测试反馈修改技能，重复测试直到满意。收尾清单：

1. 更新仓库根目录 `README.md`：目录结构 + 技能列表表格各加一行
2. `git add` → 提交（提交信息风格：`Add <name> skill: <一句话>`）
3. `git push origin main`，然后告诉用户安装方式：

```bash
npx skills add LinFangYu123/SKILLS@<skill-name>
# 或
pi install git:github.com/LinFangYu123/SKILLS
```

## 修改现有技能时

- **保留原目录名和 frontmatter 的 name**，不要重命名
- 改动前先想清楚用户要的是「行为变化」还是「表述优化」，前者要重测触发
- 若修改了调用策略（加/去掉 `disable-model-invocation`），SKILL.md 与
  `agents/openai.yaml` 必须**同步改**，两者永远保持一致
