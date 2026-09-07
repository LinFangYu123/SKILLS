---
name: code-review
description: Review code by file type — auto-detect the language, load the matching language checklist, and record user-confirmed findings into a persistent ledger for future reviews. Merges duplicate issue patterns and can leverage code-graph tools (ctags/joern/tree-sitter) for cross-file analysis. Use when asked to review code, 代码审查/代码review/check this code, review my changes/diff/PR, 帮我看看这段代码有什么问题, find bugs or security issues, or critique implementation.
version: "1.0.0"
---

# Code Review（按语言细分的代码审查）

对指定代码做**按语言定制**的审查：识别文件类型 → 只加载对应语言的
审查清单 → 结合历史问题台账 → 输出问题清单。经用户确认的问题写入
台账，同类问题自动合并，让每次 review 都沉淀为下一次的经验。

## 工作流程（六步，按序执行）

### Step 1 · 圈定范围

确定 review 对象，按优先级取其一：

1. 用户显式指定的文件/目录
2. `git diff`（含暂存区）——用户说「review 我的改动」时
3. 当前会话刚写/改过的文件

超过 20 个文件时，先列文件清单请用户确认范围，避免注意力摊薄。

### Step 2 · 识别语言，加载对应清单

按扩展名和构建清单（`package.json` / `pyproject.toml` / `go.mod` /
`Cargo.toml`）判定每份文件的语言，**只加载命中的语言清单**：

| 语言 | 清单 |
|---|---|
| Python | [references/python.md](./references/python.md) |
| TypeScript / JavaScript | [references/typescript.md](./references/typescript.md) |
| Go | [references/golang.md](./references/golang.md) |
| C / C++ | [references/c-cpp.md](./references/c-cpp.md) |
| Java | [references/java.md](./references/java.md) |
| Rust | [references/rust.md](./references/rust.md) |
| 其他/未知 | [references/general.md](./references/general.md) |

多语言混合时逐份加载对应清单，不加载未命中的。每份清单都是
「必查项」级别——清单里列出的类别必须逐项过一遍，而不是凭感觉抽查。

### Step 3 · 检测代码图谱工具（可选辅助）

运行探测，有则用、无则跳过、**不阻塞**：

```bash
command -v ctags universal-ctags joern tree-sitter
```

- `universal-ctags`：先生成符号表（`ctags -R -x` 或 tags 文件），
  用于核对「定义了但无人调用」的函数、跨文件引用关系
- `joern` / `tree-sitter`：对 C/C++、多语言做调用图与数据流查询，
  适合追「这个值从哪来、传到哪去」类问题
- 都没有时退化为手动 grep 追引用——只对可疑点做定点追踪，
  不做全库扫描

代码图谱的产出只服务于两个判断：**死代码**和**跨文件的数据流/控制流
问题**（如未校验的外部输入流入敏感操作）。

### Step 4 · 读取历史台账

台账按「语言 / 分类」分文件存放于 `references/ledger/<语言>/<分类>.md`
（如 `references/ledger/python/api-design.md`，目录名与 Step 2 的语言
清单、Step 6 的分类标签保持同名）。**每次 review 前必读**本次命中
语言的全部台账文件（`ls references/ledger/<语言>/`）：

- 台账中的每类问题都是**重点检查项**——先查本批代码是否复现同类问题
- 复现的，直接按台账既有条目呈报并累加次数（见 Step 6 合并规则）
- 对应目录不存在或无文件则跳过本步

### Step 5 · 执行审查并呈报

按语言清单逐项检查，输出问题清单。每条问题必须包含：

- **位置**：`文件路径:行号`
- **严重度**：🔴 缺陷/安全 / 🟡 隐患/坏味道 / 🔵 风格/可维护性
- **说明**：为什么是问题（引用清单条目或台账条目），不写空泛评语
- **修复建议**：可操作的改法，关键处给代码片段

呈报完**停下来等用户确认**——哪些问题成立、哪些误报/可接受，
由用户逐条或批量裁决。未经确认的问题一律不写入台账。

### Step 6 · 记录确认的问题（合并去重）

对用户确认的每条问题：

1. 在台账中按**分类标签**（如 `error-handling`、`memory-safety`、
   `concurrency`）和**模式**（问题本质，剥离具体文件名）查重
2. 命中既有条目 → **合并**：`次数 +1`、追加新例证到「已知例证」、
   更新「最近发现」日期；不再新增条目
3. 未命中 → 新增条目，写入 `references/ledger/<语言>/<分类>.md`；
   文件不存在时按 [references/ledger/README.md](./ledger/README.md)
   的格式新建，**不预建空文件**
4. 语言归属：按被审文件的语言归档；仅有 general.md 兑底清单覆盖的
   文件（shell/配置等）归 `references/ledger/general/<分类>.md`

台账是**唯一事实源**：同一语言同一分类只存在一个文件，合并后
一个模式只存在一个条目。当某模式累计 ≥5 次时，在该条目加
「⚠ 高频」标记，后续 review 优先检查。

## 完成判据

- [ ] 清单中每个类别都已过检（不是抽查）
- [ ] 每条发现都有位置、严重度、依据、修复建议
- [ ] 用户已对每条发现裁决（确认/驳回）
- [ ] 确认的问题已写入台账，同类已合并、无重复模式
- [ ] 台账中「⚠ 高频」模式已在本轮 review 中重点复查过

## 执行规则

- **只读代码**：除台账外不改动目标代码库任何文件，不顺手修复——
  修复是 review 确认后的独立任务
- **先查后报**：引用台账条目或清单条目作为依据，误报会消耗用户信任
- **诚实标注不确定**：拿不准的标注「待确认」，单独归为一类，
  不与确定问题混排
