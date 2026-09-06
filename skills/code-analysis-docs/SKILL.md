---
name: code-analysis-docs
description: Analyze a codebase and produce evidence-based technical documentation — architecture report, module walkthrough, API reference, or README. Multi-phase workflow (recon → deep dive → quality → synthesis) with confidence tracking and file-path citations. Use when asked to 分析代码库, document architecture, 梳理项目结构, generate 技术文档/架构报告/README, or when mentioning "analyze this codebase", "what does this project do", "code audit", "architecture review".
version: "1.0.0"
---

# Code Analysis Docs（代码分析 → 技术文档）

对目标代码库做**证据驱动**的多阶段分析，产出引用真实文件路径、
区分事实与推断的结构化技术文档。全程只读代码，只写文档本身。

## 何时使用

- 用户给出项目路径，要求"分析一下这个项目""梳理架构""写技术文档"
- 接手陌生代码库，需要快速摸底（模块划分、核心流程、依赖关系）
- 要求为项目生成 README、API 参考或模块说明
- 要求"代码审计/架构评审"式的报告

## 不适用

- 只想搜一处代码或改一个文件 → 直接用搜索/编辑工具
- 无证据的猜测性结论 —— 本技能的铁律是**先调查后结论**

## 工作流程（五阶段，按序执行，勿跳过）

### Phase 1 · 侦察（广度扫描，约占 20% 精力）

目标：不逐文件阅读就建立整体地图。

1. 列顶层目录结构（2–3 层深），注意目录布局与命名惯例
2. **优先读清单/配置文件**：
   - 构建清单：`package.json` / `Cargo.toml` / `go.mod` / `pyproject.toml` /
     `pom.xml` / `Makefile` / `CMakeLists.txt` / `*.mk` / `*.csproj`
   - CI/配置：`.github/workflows/*` / `Dockerfile` / `.editorconfig` / lint 配置
   - 文档：`README.md` / `ARCHITECTURE.md` / `docs/` / `AGENTS.md`
3. 识别多模块/monorepo 结构：包、模块、服务及其关系
4. 根据扩展名、import、清单盘点语言与框架

### Phase 2 · 架构深潜（约占 35% 精力）

1. **找入口点**：`main.*` / CLI 入口 / 路由定义 / 服务启动文件
2. **追踪核心流程**：端到端跟 3–5 条关键路径（如：请求 → 处理 → 存储 → 响应），
   其余流程给出可自行追踪的文件索引
3. **画内部依赖图**：哪个模块依赖哪个；标注跨模块耦合点
4. **识别架构模式**：单体/微服务/事件驱动/分层/插件式……
5. 检查数据层：存储格式、schema、迁移、缓存策略

### Phase 3 · 质量评估（约占 25% 精力）

1. **测试**：目录结构、框架、单测/集成/e2e 比例、有无覆盖配置、明显缺口
2. **错误处理**：如何传播？集中处理？日志策略？
3. **类型与校验**：严格模式、lint、运行时校验、空安全
4. **安全**：认证授权模式、密钥管理、输入净化、依赖漏洞线索
5. **代码一致性**：命名、组织、抽象层次、重复度

### Phase 4 · 基建与运维（约占 20% 精力）

构建系统 → CI/CD 流水线 → 部署模型 → 可观测性 → 环境差异（dev/staging/prod）。
嵌入式项目另查：交叉工具链、defconfig、镜像烧写方式。

### Phase 5 · 综合成文

按 `references/output-template.md` 的模板写输出文档。

## 执行规则

**必做：**
- **先读后写**：Phase 1–4 完成前不生成文档
- **引用具体文件**：每条论断给出证据路径（如 `base/list.c:120`），不做无出处的一般性评论
- **诚实标注不确定**：无法确定的内容显式说明；置信度 < 5/5 时附 `△ Caveats`
- **分节增量写**：完成一个阶段写一节，不要憋到最后一次性输出
- **只读分析**：除输出文档外不改动目标代码库任何文件
- **验证文档示例**：文档中的示例代码须实际编译/运行验证（Python `pytest --doctest-modules`、TS `tsc --noEmit`、C 实际 `gcc` 编译），验证不过就修到过

**取舍策略：**
- 深度优先于广度：入口点 > 配置 > 核心领域逻辑 > 工具类 > 测试 > 生成代码
- 跳过 vendored 依赖、生成代码、模板性样板
- >500 文件的代码库聚焦最重要的 2–3 个模块，并在执行摘要里声明分析范围
- 优先读小而关键的文件，避免在超大文件上耗尽上下文

## 置信度追踪（调查过程中持续维护）

| 条 | 级 | 名称 | 含义 |
|----|----|------|------|
| `░░░░░` | 0 | Gathering | 初始取证 |
| `▓░░░░` | 1 | Surveying | 广度扫描，浮现模式 |
| `▓▓░░░` | 2 | Investigating | 深潜、验证模式 |
| `▓▓▓░░` | 3 | Analyzing | 交叉印证、补缺口 |
| `▓▓▓▓░` | 4 | Synthesizing | 连接发现，高置信 |
| `▓▓▓▓▓` | 5 | Concluded | 交付结论 |

- 每步取证后输出：**Confidence / Found / Patterns / Gaps / Next**
- 证据来源优先级：直接读代码 > 文档注释 > 测试 > git 历史 > 外部检索 > 推理 > （显式标注的）假设
- 校准：清晰代码库 + 明确问题 → 从 2–3 起步；模糊或复杂 → 从 0–1 起步
- 4 级时可询问："再补一个角度即可满置信，继续还是现在交付？"

## 产出物（按任务类型选一或组合）

1. **架构分析报告**（默认）→ `{项目根}/{项目名}_ANALYSIS.md`
2. **README / 快速上手** → 项目根 `README.md` 或独立文件
3. **API 参考** → 按语言风格（Doxygen / JSDoc / Google docstring / OpenAPI）
4. **ADR（架构决策记录）** → 编号记录 Context/Decision/Rationale/Consequences

## 文档写作原则

- 示例胜过解释：show, don't tell
- 注释解释 **WHY** 而非 WHAT；过时注释比没注释更糟
- 渐进披露：Quick Start 在前，细节在后
- 架构图用简洁 ASCII 图，不追求图形花哨
- 文档跟着代码走：放同一仓库、贴近相关代码
