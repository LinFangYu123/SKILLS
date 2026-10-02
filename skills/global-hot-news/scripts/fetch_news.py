#!/usr/bin/env python3
"""抓取全球头条（The Hear）+ 国内热点源的零依赖脚本。

只用标准库，输出 JSON 到 stdout，供 agent 组织成中文简报。

    python3 scripts/fetch_news.py --countries us,china,uk --limit 5
    python3 scripts/fetch_news.py --countries all --sources cn --limit 8
    python3 scripts/fetch_news.py --list

数据源：
  The Hear  https://www.thehear.org/api/country-view/<country>   （公开、免 key、20 国）
  微博热搜  https://weibo.com/ajax/side/hotSearch
  腾讯新闻  https://i.news.qq.com/web_backend/v2/getTagInfo?tagId=aEWqxLtdgmQ%3D
  华尔街见闻 https://api-one.wallstcn.com/apiv1/content/information-flow
  少数派    https://sspai.com/feed
  InfoQ 中文 https://www.infoq.cn/feed.xml
  France 24 https://www.france24.com/en/rss
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# The Hear 支持的 20 个国家；DEFAULT 是「每天先扫一遍」的热区。
COUNTRIES = ["china", "us", "uk", "russia", "ukraine", "israel", "palestine",
             "iran", "lebanon", "france", "germany", "italy", "spain",
             "netherlands", "poland", "finland", "turkey", "india", "japan", "kenya"]
DEFAULT_COUNTRIES = ["china", "us", "uk", "russia", "ukraine", "israel", "iran"]


def http(url, referer=None, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        **({"Referer": referer} if referer else {}),
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_json(url, referer=None, timeout=15):
    return json.loads(http(url, referer, timeout).decode("utf-8", "replace"))


def clean_link(url):
    """个别源把域名前缀重复拼进链接（…pravda.com.uahttps://www.pravda.com.ua/news/…），
    取后半段完整的那个。"""
    url = (url or "").strip()
    if not url:
        return ""
    idx = url.find("http", 5)
    if idx > 0 and url[:idx].rstrip("/") in url[idx:]:
        return url[idx:]
    return url


def strip_tags(text, limit=300):
    """RSS 摘要常带 HTML 标签，压成一行纯文本。"""
    out, in_tag = [], False
    for ch in text or "":
        if ch == "<":
            in_tag = True
        elif ch == ">":
            in_tag = False
        elif not in_tag:
            out.append(ch)
    return " ".join("".join(out).split())[:limit]


def rss_items(url, limit):
    """极简 RSS 2.0 / Atom 解析：标题、链接、时间。"""
    root = ET.fromstring(http(url))
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = []
    for node in root.iter():
        tag = node.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        title = link = when = ""
        for child in node:
            name = child.tag.split("}")[-1]
            if name == "title":
                title = strip_tags(child.text or "", 200)
            elif name == "link":
                link = (child.get("href") or child.text or "").strip()
            elif name in ("pubDate", "published", "updated", "date"):
                when = (child.text or "").strip()
        if title:
            items.append({"title": title, "url": link, "time": when})
        if len(items) >= limit:
            break
    return items


# ---- 全球头条：The Hear ------------------------------------------------

def fetch_hear(country, limit):
    data = http_json(f"https://www.thehear.org/api/country-view/{country}")
    headlines = [{
        "source": h.get("sourceLabel", ""),
        "headline": strip_tags(h.get("headline", ""), 220),
        "subtitle": strip_tags(h.get("subtitle", ""), 160),
        "link": clean_link(h.get("link", "")),
        "captured_at": h.get("capturedAt", ""),
    } for h in (data.get("headlines") or [])[:limit]]
    overview = ((data.get("overviews") or {}).get("current") or {}).get("summary", "")
    return {
        "country": country,
        "country_name": data.get("countryName", country),
        "as_of_utc": data.get("asOfUtc", ""),
        "source_count": len(data.get("headlines") or []),
        "headlines": headlines,
        "ai_overview": strip_tags(overview, 600),
    }


# ---- 国内热点源 --------------------------------------------------------

def fetch_weibo(limit):
    data = http_json("https://weibo.com/ajax/side/hotSearch", referer="https://weibo.com/")
    out = []
    for item in (data.get("data") or {}).get("realtime") or []:
        word = item.get("word") or item.get("note")
        if not word:
            continue
        out.append({
            "title": word,
            "url": f"https://s.weibo.com/weibo?q={urllib.parse.quote('#' + word + '#')}&Refer=top",
            "heat": str(item.get("num") or item.get("raw_hot") or ""),
        })
        if len(out) >= limit:
            break
    return out


def fetch_tencent(limit):
    data = http_json("https://i.news.qq.com/web_backend/v2/getTagInfo?tagId=aEWqxLtdgmQ%3D",
                     referer="https://news.qq.com/")
    out = []
    for tab in (data.get("data") or {}).get("tabs") or []:
        for entry in tab.get("articleList") or []:
            title = entry.get("title") or entry.get("short_title")
            if not title:
                continue
            link = (entry.get("link_info") or {}).get("url", "")
            out.append({
                "title": strip_tags(title, 160),
                "url": link,
                "time": entry.get("publish_time", ""),
                "digest": strip_tags(entry.get("desc", ""), 160),
            })
            if len(out) >= limit:
                return out
    return out


def fetch_wallstreetcn(limit):
    data = http_json("https://api-one.wallstcn.com/apiv1/content/information-flow"
                     "?channel=global-channel&accept=article&limit=30")
    out = []
    for item in (data.get("data") or {}).get("items") or []:
        res = item.get("resource") or {}
        title = res.get("title") or res.get("content_short")
        if not title:
            continue
        out.append({
            "title": strip_tags(title, 160),
            "url": res.get("uri") or res.get("web_uri") or "",
            "time": datetime.fromtimestamp(res.get("display_time", 0), timezone.utc)
                            .strftime("%Y-%m-%d %H:%M UTC") if res.get("display_time") else "",
        })
        if len(out) >= limit:
            break
    return out


CN_SOURCES = {
    "weibo": ("微博热搜", fetch_weibo),
    "tencent": ("腾讯新闻", fetch_tencent),
    "wallstreetcn": ("华尔街见闻", fetch_wallstreetcn),
    "sspai": ("少数派", lambda n: rss_items("https://sspai.com/feed", n)),
    "infoq": ("InfoQ 中文", lambda n: rss_items("https://www.infoq.cn/feed.xml", n)),
}
INTL_RSS = {
    "france24": ("France 24", "https://www.france24.com/en/rss"),
}


def main():
    ap = argparse.ArgumentParser(description="全球头条 + 国内热点抓取（零依赖）")
    ap.add_argument("--countries", default=",".join(DEFAULT_COUNTRIES),
                    help="The Hear 国家键，逗号分隔；all = 全部 20 国。默认热区：" +
                         ",".join(DEFAULT_COUNTRIES))
    ap.add_argument("--sources", default="cn,intl",
                    help="补充源分组：cn(国内) / intl(国际) / both，逗号分隔")
    ap.add_argument("--skip", nargs="*", default=[],
                    help="跳过的源键，如 weibo tencent")
    ap.add_argument("--limit", type=int, default=5, help="每个源取几条，默认 5")
    ap.add_argument("--list", action="store_true", help="列出国家键与源键后退出")
    args = ap.parse_args()

    if args.list:
        print("The Hear 国家键:", ", ".join(COUNTRIES))
        print("热区默认:", ", ".join(DEFAULT_COUNTRIES))
        print("国内源:", ", ".join(f"{k}({v[0]})" for k, v in CN_SOURCES.items()))
        print("国际源:", ", ".join(f"{k}({v[0]})" for k, v in INTL_RSS.items()))
        return

    wanted = COUNTRIES if args.countries.strip() == "all" else \
        [c.strip() for c in args.countries.split(",") if c.strip()]
    groups = {g.strip() for g in args.sources.split(",") if g.strip()}
    errors = []

    result = {
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit_per_source": args.limit,
        "hear": {},
        "cn": {},
        "intl": {},
        "errors": errors,
    }

    for country in wanted:
        if country not in COUNTRIES:
            errors.append(f"unknown country key: {country}")
            continue
        try:
            result["hear"][country] = fetch_hear(country, args.limit)
        except Exception as exc:                                  # noqa: BLE001
            errors.append(f"hear/{country}: {type(exc).__name__}: {exc}")

    if groups & {"cn", "both"}:
        for key, (label, fn) in CN_SOURCES.items():
            if key in args.skip:
                continue
            try:
                items = fn(args.limit)
                if items:
                    result["cn"][key] = {"label": label, "items": items}
                else:
                    errors.append(f"{key}: 0 items")
            except Exception as exc:                              # noqa: BLE001
                errors.append(f"{key}: {type(exc).__name__}: {exc}")

    if groups & {"intl", "both"}:
        for key, (label, url) in INTL_RSS.items():
            if key in args.skip:
                continue
            try:
                items = rss_items(url, args.limit)
                if items:
                    result["intl"][key] = {"label": label, "items": items}
                else:
                    errors.append(f"{key}: 0 items")
            except Exception as exc:                              # noqa: BLE001
                errors.append(f"{key}: {type(exc).__name__}: {exc}")

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
