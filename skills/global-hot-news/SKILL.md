---
name: global-hot-news
description: 全球热点新闻速览：抓 The Hear 20 国头版头条 + 国内热搜与主流媒体，产出带来源链接的中文简报。用户问「今天全球有什么热点」「国际新闻」「各国头条都在报什么」「世界/外面发生了什么」「全球新闻」「global news / world news today」时用。
version: "1.1.0"
---

# Global Hot News（全球热点速览）

一次抓两份原料：**The Hear** 的 20 国头版头条（每国 12–39 家媒体，含中国）
和**国内源**（微博热搜、腾讯新闻、华尔街见闻、少数派、InfoQ 中文）+ 一处
国际补充（France 24），组织成一份带来源链接的中文简报，直接在对话里给出。
定时任务模式下改成写入 IMA 笔记、微信只发一条通告（见文末「定时任务模式」）。

配套脚本 `scripts/fetch_news.py` 零依赖（只用标准库），`python3` 直接跑。

## 何时用 / 何时不用

用：用户想看**当下世界在发生什么**——国际时政头条、各国媒体各自把什么当头条、
和国内热点对照。

不用：

- 只问 AI 圈动态 → `ai-hot-daily`
- 只要 GitHub / arXiv / 技术博客 → `daily-tech-intel`
- 已经在聊某一条具体新闻、要深挖细节 → 直接 web_search / web_extract 追原文，
  不必跑全量抓取

## 第一步：抓取

```bash
python3 scripts/fetch_news.py                                    # 默认热区 7 国 + 国内源 + France 24
python3 scripts/fetch_news.py --countries us,china,uk --limit 5  # 指定国家
python3 scripts/fetch_news.py --countries all --limit 3          # 全部 20 国
python3 scripts/fetch_news.py --sources cn --limit 8             # 只要国内源
python3 scripts/fetch_news.py --list                             # 列国家键与源键
```

选国家的判据：用户点名了照办；没点名就先扫默认热区
（china/us/uk/russia/ukraine/israel/iran），看完头条判断当天焦点，
需要再补一轮其他国家键（`--list` 给出全部 20 国）。一次调用约 7 秒，
多跑一两轮的代价很低。

输出 JSON：`hear.<国家>.headlines[]`（`source`/`headline`/`subtitle`/`link`/`captured_at`）
与 `hear.<国家>.ai_overview`（AI 概述）、`cn.<源>.items[]`、`intl.france24.items[]`、
`errors[]`。**先看 `errors`**：非空说明有源这轮没拿到。

## 第二步：读原文，再动笔

- 非英语头条是原文（俄语、乌克兰语、希伯来语、波斯语…），**译成中文**，
  人名地名用通行译名，需要时括号附原文
- `ai_overview` 是 AI 生成的解释层，**头条原文才是事实源**：两者冲突时以原文为准，
  不把概述里的内容当事实写
- 同一事件被多国报道时**并列写各国框架**——谁把它当头条、措辞差在哪。
  这个对照本身就是产出，不要合成一个「中立版本」
- 头条只有一行，判断不了细节时标「（标题层面）」，不补脑细节

## 第三步：产出简报（对话内，纯文本）

骨架：

```
全球热点速览 YYYY-MM-DD

一、全球头条

1、<事件> —— <一到三句：发生了什么、各方怎么说>
   美 <媒体名>：「<头条译>」https://…
   俄 <媒体名>：「<头条译>」https://…

2、<事件> —— …

二、国内热点

1、<事件> —— <说明>（来源：<源名> https://…）

2、<事件> —— …
```

排版与内容要求：

- 纯文本输出，不用 Markdown 表格、星号、井号标题——所在 CLI 不渲染 Markdown，
  符号会原样显示
- 每条带**来源名 + 完整 URL**（The Hear 的头条用 `link`，国内源用 `url`）。
  个别源本轮没给 `link`（如 RIA Novosti、FAZ）：优先换同国其他有链接的头条；
  事件非写不可时保留，并在该条末尾标「（该源未提供链接）」
- 数量：全球头条 5–8 条、国内热点 5–8 条，按重要性排序
- 同一事件的多国头条收在同一个序号下（缩进行列出），不拆成多条
- 数字、人名、地名照抄抓到的原文，不换算、不推测
- 不写「数据采集时间/来源说明」这类后记；只在 `errors` 非空时补一行
  「未取到：<源名>（<原因>）」

完成判据：全球头条 ≥5 条、国内热点 ≥5 条，每条都带来源名，除标注
「该源未提供链接」的条目外都能点开对应 URL；没有占位条目，也没有凭记忆补的旧闻。

## 定时任务模式：写入 IMA 笔记 + 微信只发一条通告

每天早上 7:00 的定时任务（「全球热点晨报」）走这一节：简报正文进 IMA 笔记，
微信只收一条通告。交互式对话仍按第三步直接在对话里给结果。

笔记标题用**前一天**的日期（7:00 抓到的快照覆盖过去约 24 小时）。

用 ima-skill 的 notes 模块**每天新建一篇**（`import_doc`，`content_format=1`），
不追加到旧笔记：

```bash
IMA_DIR=~/.hermes/skills/note-taking/ima-skill
OPTS=$(printf '{"clientId":"%s","apiKey":"%s"}' "$(cat ~/.config/ima/client_id)" "$(cat ~/.config/ima/api_key)")
# 正文（含真实 \n\n 空行）先用 write_file 落成 body.json，命令行只出现路径
node "$IMA_DIR/ima_api.cjs" "openapi/note/v1/import_doc" "$(cat /path/to/body.json)" "$OPTS"
```

- 笔记没有单独的标题字段：标题行就是正文首行
- 不要把带中文的 JSON body 拼进命令行——cron 的安全扫描会直接拒绝，先落盘再
  `"$(cat 路径)"`
- 完成判据：返回 `code: 0` 且 `data.note_id` 非空；再用 `get_doc_content`
  （`target_content_format=1`）读回抽查排版——每个段标题前、每个 `N、` 条目前
  都有空行
- 失败就停下按 `msg` 报告，**不追加到旧笔记兜底**；微信改推失败原因，不推未经
  整理的抓取结果
- 微信那条**只有两行**，不带任何内容信息（不要要点、不要条数、不贴链接、
  不复述正文）：

```
全球热点速览 YYYY-MM-DD
已写入 IMA 笔记。
```

## 源可用性（2026-10-02 本机实测）

可直连：
- The Hear（20 国头版，免 key）
- 微博热搜、腾讯新闻、华尔街见闻、少数派、InfoQ 中文
- France 24

取不到（本机网络下不可达或返回空，别反复重试）：
- BBC、The Guardian、Al Jazeera、Reuters（经 Google News 中转）
- V2EX、36kr、GitHub Trending、HuggingFace

脚本对每个源独立捕获异常：单源失败只写进 `errors`，其余照常返回。
偶发超时（`TimeoutError` / `URLError`）时原样重跑一次；连续两次失败就按上面
的格式在简报末尾说明缺失，**不用旧闻或搜索结果顶替**。

## 环境注意

- 零依赖：任意 `python3`（≥3.8）可跑，不需要 venv、不需要 requests
- 需要 Python 处理时写成 `.py` 文件再跑；`python3 -c` 这类内联脚本在 cron /
  安全扫描下会被直接拦掉
- 脚本只读公开接口：不写文件、不改系统状态
