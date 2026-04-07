import calendar
import concurrent.futures
import html
import os
import re
import ssl
import webbrowser
from datetime import datetime, timedelta

import feedparser
import pytz
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator

ssl._create_default_https_context = ssl._create_unverified_context

beijing_tz = pytz.timezone("Asia/Shanghai")
now_bj = datetime.now(beijing_tz)
cutoff = now_bj - timedelta(hours=24)
translator = GoogleTranslator(source="auto", target="zh-CN")

DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ai-daily-news")
MAX_ITEMS_PER_CATEGORY = 20

PRIMARY_AI_KEYWORDS = {
    "人工智能",
    "ai",
    "大模型",
    "生成式",
    "多模态",
    "智能体",
    "agent",
    "llm",
    "chatgpt",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "gpt",
    "deepseek",
    "qwen",
    "kimi",
    "智谱",
    "grok",
    "llama",
    "copilot",
    "sora",
    "midjourney",
}
SECONDARY_AI_KEYWORDS = {
    "推理",
    "模型",
    "训练",
    "微调",
    "世界模型",
    "token",
    "prompt",
    "embedding",
    "inference",
    "reasoning",
}
HARDWARE_KEYWORDS = {
    "ai芯片",
    "ai 算力",
    "ai算力",
    "gpu",
    "npu",
    "xpu",
    "算力",
    "芯片",
    "半导体",
    "数据中心",
    "机架",
    "英伟达",
    "nvidia",
    "amd",
    "h100",
    "b200",
    "blackwell",
}
EMBODIED_KEYWORDS = {
    "机器人",
    "具身",
    "自动驾驶",
    "辅助驾驶",
    "无人驾驶",
    "智能眼镜",
    "ai眼镜",
    "眼镜",
    "头显",
    "robot",
}
POLICY_KEYWORDS = {
    "融资",
    "募资",
    "投资",
    "收购",
    "并购",
    "估值",
    "政策",
    "监管",
    "法案",
    "法规",
    "禁令",
    "财报",
    "ipo",
}
NEGATIVE_KEYWORDS = {
    "dlss",
    "frame generation",
    "游戏",
    "显卡玩家",
    "轿跑",
    "suv",
    "航班",
    "盘前",
    "股价",
    "足球",
    "电影",
    "演唱会",
    "优惠券",
    "补贴券",
    "gaming",
    "game ready",
    "geforce",
    "vehicle launch",
    "新车",
    "轿车",
    "销量",
    "财经",
    "大盘",
}

TITLE_NEGATIVE_KEYWORDS = {
    "dlss",
    "路径追踪",
    "geforce",
    "玩家",
    "游戏",
    "suv",
    "轿跑",
    "新车",
    "mg 4x",
    "mg 07",
}

REQUIRE_EXPLICIT_AI_SOURCES = {"IT之家", "36Kr AI", "The Verge", "Ars Technica"}

SOURCE_TITLE_BLACKLIST = {
    "IT之家": {"suv", "轿跑", "dlss", "游戏", "首发", "新车", "玩家"},
    "36Kr AI": {"盘前", "股价", "航班", "晚报", "收盘", "开盘"},
    "The Verge": {"gaming", "game", "dlss", "playstation", "xbox"},
    "Ars Technica": {"gaming", "game", "dlss", "gpu review"},
}

source_matrix = [
    {
        "name": "机器之心",
        "type": "rss",
        "lang": "zh",
        "url": "https://www.jiqizhixin.com/rss",
        "strict_filter": False,
        "min_score": 2,
    },
    {
        "name": "AIbase",
        "type": "custom_aibase",
        "lang": "zh",
        "url": "https://news.aibase.com/zh/news",
        "strict_filter": False,
        "min_score": 2,
    },
    {
        "name": "TechCrunch AI",
        "type": "rss",
        "lang": "en",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "strict_filter": False,
        "min_score": 2,
    },
    {
        "name": "VentureBeat AI",
        "type": "rss",
        "lang": "en",
        "url": "https://venturebeat.com/category/ai/feed/",
        "strict_filter": False,
        "min_score": 2,
    },
    {
        "name": "AI News",
        "type": "rss",
        "lang": "en",
        "url": "https://www.artificialintelligence-news.com/feed/",
        "strict_filter": False,
        "min_score": 2,
    },
    {
        "name": "MarkTechPost",
        "type": "rss",
        "lang": "en",
        "url": "https://www.marktechpost.com/feed/",
        "strict_filter": False,
        "min_score": 2,
    },
    {
        "name": "IT之家",
        "type": "rss",
        "lang": "zh",
        "url": "https://www.ithome.com/rss/",
        "strict_filter": True,
        "min_score": 4,
    },
    {
        "name": "36Kr AI",
        "type": "rss",
        "lang": "zh",
        "url": "https://36kr.com/feed",
        "strict_filter": True,
        "min_score": 4,
    },
    {
        "name": "The Verge",
        "type": "rss",
        "lang": "en",
        "url": "https://www.theverge.com/rss/index.xml",
        "strict_filter": True,
        "min_score": 4,
    },
    {
        "name": "Ars Technica",
        "type": "rss",
        "lang": "en",
        "url": "http://feeds.arstechnica.com/arstechnica/index",
        "strict_filter": True,
        "min_score": 4,
    },
]

results = []
seen_keys = set()


def clean_html(raw_html):
    text = re.sub(re.compile("<.*?>"), "", str(raw_html))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(*parts):
    return " ".join(part for part in parts if part).lower()


def has_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def ai_relevance_score(title, summary):
    title_text = normalize_text(title)
    body_text = normalize_text(title, summary)
    score = 0
    if has_any(title_text, PRIMARY_AI_KEYWORDS):
        score += 3
    if has_any(body_text, PRIMARY_AI_KEYWORDS):
        score += 2
    if has_any(body_text, SECONDARY_AI_KEYWORDS):
        score += 1
    if has_any(body_text, HARDWARE_KEYWORDS):
        score += 1
    if has_any(body_text, EMBODIED_KEYWORDS):
        score += 1
    if has_any(body_text, POLICY_KEYWORDS):
        score += 1
    return score


def explicit_ai_signal_count(title, summary):
    content = normalize_text(title, summary)
    signals = 0
    for keyword_group in (PRIMARY_AI_KEYWORDS, HARDWARE_KEYWORDS, EMBODIED_KEYWORDS):
        if has_any(content, keyword_group):
            signals += 1
    return signals


def should_exclude_story(title, summary):
    title_text = normalize_text(title)
    content = normalize_text(title, summary)
    if has_any(title_text, TITLE_NEGATIVE_KEYWORDS):
        return True
    if has_any(content, NEGATIVE_KEYWORDS) and not has_any(
        content, PRIMARY_AI_KEYWORDS
    ):
        return True
    if has_any(
        content, {"盘前", "美股", "a股", "港股", "涨跌", "概念股"}
    ) and not has_any(content, PRIMARY_AI_KEYWORDS | HARDWARE_KEYWORDS):
        return True
    if "汽车" in content and not has_any(
        content,
        {"自动驾驶", "辅助驾驶", "智能驾驶", "无人驾驶", "具身", "ai", "机器人"},
    ):
        return True
    if has_any(content, {"发布会", "首发", "开售", "上市"}) and not has_any(
        content, PRIMARY_AI_KEYWORDS | EMBODIED_KEYWORDS
    ):
        return True
    return False


def violates_source_policy(title, source_name):
    return has_any(
        normalize_text(title), SOURCE_TITLE_BLACKLIST.get(source_name, set())
    )


def is_pure_ai_news(title, summary, strict=False, source_name="", min_score=None):
    if violates_source_policy(title, source_name):
        return False
    if should_exclude_story(title, summary):
        return False
    score = ai_relevance_score(title, summary)
    threshold = 3 if strict else 2
    if min_score is not None:
        threshold = max(threshold, min_score)
    if (
        source_name in REQUIRE_EXPLICIT_AI_SOURCES
        and explicit_ai_signal_count(title, summary) == 0
    ):
        return False
    return score >= threshold


def summarize_text(summary, limit=120):
    summary = clean_html(summary)
    if len(summary) <= limit:
        return summary
    trimmed = summary[:limit].rsplit(" ", 1)[0].strip()
    trimmed = trimmed or summary[:limit].strip()
    return trimmed + "..."


def translate_text(text):
    try:
        return translator.translate(text)
    except Exception:
        return text


def add_result(config, title, link, dt_bj, summary):
    normalized_title = re.sub(r"\s+", " ", title).strip()
    unique_key = (normalized_title.lower(), link)
    if unique_key in seen_keys:
        return
    if not is_pure_ai_news(
        title,
        summary,
        strict=config["strict_filter"],
        source_name=config["name"],
        min_score=config.get("min_score"),
    ):
        return
    if dt_bj < cutoff or dt_bj > now_bj + timedelta(hours=2):
        return

    seen_keys.add(unique_key)
    display_title = normalized_title
    display_summary = summarize_text(summary)
    if config["lang"] == "en":
        display_title = translate_text(display_title)
        if display_summary:
            display_summary = summarize_text(translate_text(display_summary), limit=90)

    results.append(
        {
            "source": config["name"],
            "title": display_title,
            "original_title": normalized_title if config["lang"] == "en" else "",
            "link": link,
            "time": dt_bj.strftime("%Y-%m-%d %H:%M"),
            "timestamp": dt_bj.timestamp(),
            "summary": display_summary,
        }
    )


def fetch_rss(config):
    try:
        parsed = feedparser.parse(config["url"])
        for entry in parsed.entries:
            if not hasattr(entry, "published_parsed") or not entry.published_parsed:
                continue
            ts = calendar.timegm(entry.published_parsed)
            dt_utc = datetime.fromtimestamp(ts, pytz.UTC)
            dt_bj = dt_utc.astimezone(beijing_tz)
            add_result(
                config,
                entry.title,
                entry.link,
                dt_bj,
                clean_html(entry.get("summary", "")),
            )
    except Exception:
        pass


def fetch_aibase(config):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(config["url"], headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.find_all(
            "a", href=lambda href: href and href.startswith("/zh/news/")
        )
        for item in items:
            title_node = item.find("div", class_=re.compile(r"md:text-\[18px\]"))
            if not title_node:
                continue
            title = title_node.text.strip()
            link = "https://news.aibase.com" + item.get("href")
            summary_node = item.find(
                "div", class_=re.compile(r"text-\[14px\].*tipColor")
            )
            summary = summary_node.text.strip() if summary_node else ""
            time_node = item.find("i", class_=re.compile(r"icon-rili"))
            dt_bj = now_bj
            if time_node and time_node.parent:
                raw_time = time_node.parent.text.strip()
                if "刚刚" in raw_time:
                    dt_bj = now_bj
                elif "分钟前" in raw_time:
                    match = re.search(r"\d+", raw_time)
                    if match:
                        dt_bj = now_bj - timedelta(minutes=int(match.group()))
                elif "小时前" in raw_time:
                    match = re.search(r"\d+", raw_time)
                    if match:
                        dt_bj = now_bj - timedelta(hours=int(match.group()))
                elif "昨天" in raw_time:
                    dt_bj = now_bj - timedelta(days=1)
                elif "-" in raw_time:
                    parts = raw_time.split("-")
                    if len(parts) == 3:
                        dt_bj = beijing_tz.localize(
                            datetime.strptime(raw_time, "%Y-%m-%d")
                        )
                    elif len(parts) == 2:
                        dt_bj = beijing_tz.localize(
                            datetime.strptime(f"{now_bj.year}-{raw_time}", "%Y-%m-%d")
                        )
            add_result(config, title, link, dt_bj, summary)
    except Exception:
        pass


def classify_item(item):
    content = normalize_text(item["title"], item["summary"], item["original_title"])
    if has_any(content, POLICY_KEYWORDS):
        return "政策风向与投融资"
    if has_any(content, EMBODIED_KEYWORDS):
        return "具身智能与智能终端"
    if has_any(content, HARDWARE_KEYWORDS):
        return "AI算力与硬件芯片"
    if has_any(content, PRIMARY_AI_KEYWORDS | SECONDARY_AI_KEYWORDS):
        return "大模型与前沿技术"
    return "综合前沿资讯"


def build_html(categories):
    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "    <title>AI 行业 24 小时精选快讯</title>",
        '    <script src="https://cdn.tailwindcss.com"></script>',
        "    <style>",
        "        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');",
        "        html { scroll-behavior: smooth; }",
        "        body { font-family: 'Inter', system-ui, -apple-system, sans-serif; background-color: #f8fafc; }",
        "        .card-hover { transition: transform 0.2s ease, box-shadow 0.2s ease; border-left: 4px solid transparent; }",
        "        .card-hover:hover { transform: translateX(4px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-left-color: #3b82f6; }",
        "        .hide-scrollbar::-webkit-scrollbar { display: none; }",
        "        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }",
        "        .en-subtitle { color: #94a3b8; font-size: 0.75rem; margin-top: 2px; }",
        "    </style>",
        "</head>",
        '<body class="text-slate-800 antialiased">',
        '    <div class="max-w-4xl mx-auto px-4 py-8 relative">',
        '        <header class="mb-6 text-center">',
        '            <h1 class="text-3xl font-bold tracking-tight text-slate-900 mb-3">AI 行业 24 小时日报</h1>',
        f'            <div class="inline-flex items-center px-4 py-1.5 rounded-full bg-slate-900 text-white text-sm font-medium shadow-sm">北京时间: {now_bj.strftime("%Y年%m月%d日")}</div>',
        "        </header>",
        '        <nav class="sticky top-0 z-50 bg-[#f8fafc]/90 backdrop-blur-md py-4 mb-8 border-b border-slate-200 hide-scrollbar overflow-x-auto">',
        '            <div class="flex flex-nowrap md:flex-wrap gap-2 justify-start md:justify-center min-w-max md:min-w-0 px-2">',
        '                <button onclick="filterCategory(\'all\', this)" class="cat-btn active px-4 py-2 rounded-full text-sm font-semibold bg-blue-600 text-white shadow-sm transition-all whitespace-nowrap border border-transparent">🌟 全部动态</button>',
    ]

    for cat_name, cat_data in categories.items():
        if cat_data["items"]:
            html_parts.append(
                f'<button onclick="filterCategory(\'{cat_data["id"]}\', this)" class="cat-btn px-4 py-2 rounded-full text-sm font-medium bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 transition-all whitespace-nowrap shadow-sm">{cat_data["icon"]} {cat_name} <span class="ml-1 text-xs px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-500">{len(cat_data["items"])}</span></button>'
            )

    html_parts.append('</div></nav><main class="space-y-12" id="news-container">')

    for cat_name, cat_data in categories.items():
        items = cat_data["items"]
        if not items:
            continue
        html_parts.append(
            f'<section id="{cat_data["id"]}" class="cat-section scroll-mt-24"><div class="flex items-center gap-3 mb-6"><span class="text-2xl">{cat_data["icon"]}</span><h2 class="text-2xl font-bold text-slate-800">{cat_name}</h2></div><div class="space-y-4 pl-2 border-l-2 border-slate-200">'
        )
        for idx, item in enumerate(items, 1):
            summary = item["summary"]
            if summary.startswith("IT之家"):
                summary = summary.split("消息，", 1)[-1].strip()
            subtitle_html = (
                f'<div class="en-subtitle font-mono truncate">{html.escape(item["original_title"])}</div>'
                if item.get("original_title")
                else ""
            )
            html_parts.append(
                f'<article class="bg-white p-5 rounded-xl shadow-sm border border-slate-200 card-hover relative group"><div class="absolute -left-3.5 top-5 w-7 h-7 bg-slate-800 text-white rounded-full flex items-center justify-center text-sm font-bold shadow-sm ring-4 ring-[#f8fafc] group-hover:bg-blue-600 transition-colors">{idx}</div><div class="ml-6 flex flex-col gap-2"><div class="flex items-center justify-between"><span class="px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-semibold rounded-md">{html.escape(item["source"])}</span><time class="text-sm text-slate-400 font-medium">{html.escape(item["time"])}</time></div><h3 class="text-lg font-bold leading-snug"><a href="{html.escape(item["link"])}" target="_blank" class="hover:text-blue-600 transition-colors">{html.escape(item["title"])}</a></h3>{subtitle_html}<p class="text-slate-500 leading-relaxed text-sm mt-1">{html.escape(summary)}</p></div></article>'
            )
        html_parts.append("</div></section>")

    html_parts.extend(
        [
            "</main>",
            '        <footer class="mt-16 text-center text-sm text-slate-400 border-t border-slate-200 pt-8 pb-12">由 Claude (AI News Skill) 自动化聚合生成 · 纯 AI 过滤优化版 · 海外资讯双语翻译</footer>',
            "    </div>",
            "    <script>",
            "        function filterCategory(catId, btnElement) {",
            "            document.querySelectorAll('.cat-btn').forEach(btn => {",
            "                btn.classList.remove('bg-blue-600', 'text-white', 'border-transparent', 'font-semibold');",
            "                btn.classList.add('bg-white', 'text-slate-600', 'border-slate-200', 'font-medium');",
            "            });",
            "            btnElement.classList.remove('bg-white', 'text-slate-600', 'border-slate-200', 'font-medium');",
            "            btnElement.classList.add('bg-blue-600', 'text-white', 'border-transparent', 'font-semibold');",
            "            document.querySelectorAll('.cat-section').forEach(sec => {",
            "                if (catId === 'all' || sec.id === catId) {",
            "                    sec.style.display = 'block';",
            "                    sec.style.opacity = '0';",
            "                    setTimeout(() => { sec.style.transition = 'opacity 0.3s ease'; sec.style.opacity = '1'; }, 10);",
            "                } else {",
            "                    sec.style.display = 'none';",
            "                }",
            "            });",
            "            if (catId !== 'all') { window.scrollTo({ top: 0, behavior: 'smooth' }); }",
            "        }",
            "    </script>",
            "</body>",
            "</html>",
        ]
    )
    return "".join(html_parts)


print("🚀 Starting strict pure-AI fetching & translating...")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    for source in source_matrix:
        if source["type"] == "rss":
            executor.submit(fetch_rss, source)
        elif source["type"] == "custom_aibase":
            executor.submit(fetch_aibase, source)

results.sort(key=lambda item: item["timestamp"], reverse=True)
print(f"✅ Extracted {len(results)} PURE AI news items after applying strict filter.")

categories = {
    "大模型与前沿技术": {"id": "model", "icon": "🤖", "items": []},
    "AI算力与硬件芯片": {"id": "hardware", "icon": "💻", "items": []},
    "具身智能与智能终端": {"id": "embodied", "icon": "🦾", "items": []},
    "政策风向与投融资": {"id": "policy", "icon": "📈", "items": []},
    "综合前沿资讯": {"id": "general", "icon": "📰", "items": []},
}

for item in results:
    category = classify_item(item)
    if len(categories[category]["items"]) < MAX_ITEMS_PER_CATEGORY:
        categories[category]["items"].append(item)

save_dir = os.path.expanduser(
    os.environ.get("AI_DAILY_NEWS_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
)
os.makedirs(save_dir, exist_ok=True)
date_str = now_bj.strftime("%Y%m%d")
output_path = os.path.join(save_dir, f"AI_Daily_News_{date_str}.html")
with open(output_path, "w", encoding="utf-8") as file:
    file.write(build_html(categories))

print(f"📝 网页生成成功: {output_path}")
webbrowser.open(f"file://{os.path.abspath(output_path)}")
