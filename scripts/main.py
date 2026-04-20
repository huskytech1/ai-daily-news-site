import calendar
import concurrent.futures
import html
import os
import re
import ssl
import threading
from difflib import SequenceMatcher
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

DEFAULT_OUTPUT_DIR = os.path.join(
    os.path.expanduser("~"), "Documents", "ai-daily-news"
)
MAX_ITEMS_PER_CATEGORY = 20
MAX_CONSECUTIVE_SAME_ACTOR = 2

SOURCE_PRIORITY = {
    "TechCrunch AI": 10,
    "VentureBeat AI": 9,
    "The Verge": 9,
    "Ars Technica": 8,
    "机器之心": 8,
    "IT之家": 7,
    "36Kr AI": 7,
    "AI News": 6,
    "MarkTechPost": 5,
    "AIbase": 3,
}

SOURCE_CREDIBILITY = {
    "TechCrunch AI": 9.5,
    "VentureBeat AI": 9.0,
    "The Verge": 8.5,
    "Ars Technica": 8.5,
    "机器之心": 8.0,
    "IT之家": 7.0,
    "36Kr AI": 7.0,
    "AI News": 6.5,
    "MarkTechPost": 6.0,
    "AIbase": 5.0,
}

TOP_TIER_ACTORS = {
    "openai",
    "google",
    "deepmind",
    "anthropic",
    "meta",
    "microsoft",
    "nvidia",
    "amazon",
    "xai",
    "deepseek",
    "alibaba",
    "baidu",
    "tencent",
    "qwen",
    "claude",
    "gemini",
    "gpt",
}

MAJOR_EVENT_KEYWORDS = {
    "发布",
    "推出",
    "上线",
    "收购",
    "融资",
    "募资",
    "投资",
    "并购",
    "监管",
    "法案",
    "法规",
    "财报",
    "ipo",
    "合作",
    "开发",
}

STRATEGIC_PRODUCT_KEYWORDS = {
    "gpt",
    "claude",
    "gemini",
    "codex",
    "copilot",
    "qwen",
    "llama",
    "rosalind",
    "veo",
    "sora",
    "midjourney",
    "agent",
    "sdk",
    "api",
    "芯片",
    "gpu",
    "机器人",
    "眼镜",
}

COMMON_ENTITY_TOKENS = {
    "ai",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "gpt",
    "llm",
    "chatgpt",
    "deepseek",
    "qwen",
    "kimi",
    "llama",
    "copilot",
    "agent",
    "agents",
    "microsoft",
    "google",
    "meta",
    "amazon",
    "aws",
    "xai",
    "baidu",
    "alibaba",
    "tencent",
    "zhipu",
    "bytedance",
    "nvidia",
    "tesla",
    "perplexity",
    "mistral",
}

GENERIC_SIMILARITY_WORDS = {
    "收购",
    "吞并",
    "融资",
    "募资",
    "投资",
    "发布",
    "推出",
    "启动",
    "升级",
    "计划",
    "能力",
    "人才",
    "初创公司",
    "公司",
    "工具",
    "模型",
    "金融",
    "理财",
    "财务",
    "提升",
    "专注",
    "实质",
    "模式",
}

ENTITY_ALIASES = {
    "microsoft 365 copilot": "copilot",
    "365 copilot": "copilot",
    "microsoft": "microsoft",
    "msft": "microsoft",
    "微软": "microsoft",
    "google": "google",
    "alphabet": "google",
    "谷歌": "google",
    "meta": "meta",
    "facebook": "meta",
    "脸书": "meta",
    "亚马逊": "amazon",
    "amazon": "amazon",
    "aws": "amazon",
    "苹果": "apple",
    "apple": "apple",
    "英伟达": "nvidia",
    "nvidia": "nvidia",
    "amd": "amd",
    "openai": "openai",
    "anthropic": "anthropic",
    "claude": "claude",
    "谷歌 deepmind": "deepmind",
    "google deepmind": "deepmind",
    "deepmind": "deepmind",
    "google photos": "googlephotos",
    "google photo": "googlephotos",
    "谷歌相册": "googlephotos",
    "个人相册": "googlephotos",
    "xai": "xai",
    "grok": "grok",
    "马斯克": "xai",
    "特斯拉": "tesla",
    "tesla": "tesla",
    "deepseek": "deepseek",
    "深度求索": "deepseek",
    "通义": "qwen",
    "qwen": "qwen",
    "阿里": "alibaba",
    "阿里巴巴": "alibaba",
    "alibaba": "alibaba",
    "腾讯": "tencent",
    "tencent": "tencent",
    "混元": "hunyuan",
    "hunyuan": "hunyuan",
    "百度": "baidu",
    "baidu": "baidu",
    "文心": "ernie",
    "ernie": "ernie",
    "智谱": "zhipu",
    "z.ai": "zhipu",
    "glm": "glm",
    "字节跳动": "bytedance",
    "豆包": "doubao",
    "bytedance": "bytedance",
    "perplexity": "perplexity",
    "mistral": "mistral",
    "hugging face": "huggingface",
    "huggingface": "huggingface",
}

MATCH_REPLACEMENTS = (
    ("智能体", "agent"),
    ("代理", "agent"),
    ("agents", "agent"),
    ("agentic", "agent"),
    ("研发", "开发"),
    ("打造", "开发"),
    ("发布了", "发布"),
    ("推出了", "发布"),
    ("上线", "发布"),
    ("面向", "针对"),
    ("整合进", "整合"),
    ("接入", "整合"),
    ("收购了", "收购"),
    ("买下", "收购"),
    ("类似", "类"),
    ("药物发现", "lifescience"),
    ("生命科学", "lifescience"),
    ("基因组学", "lifescience"),
    ("制药", "lifescience"),
    ("生物学", "lifescience"),
)

TITLE_NOISE_PATTERNS = (
    r"^(最前线|硬氪专访|硬氪|独家|快讯|观察|深度|焦点|专访)\s*[|｜:：-]\s*",
    r"\s*[|｜]\s*(最前线|硬氪专访|硬氪|独家|快讯|观察|深度|焦点|专访)$",
)

EVENT_STOPWORDS = {
    "news",
    "report",
    "today",
    "latest",
    "using",
    "based",
    "global",
    "中国",
    "美国",
    "行业",
    "最新",
    "过去",
    "小时",
    "今日",
    "目前",
    "宣布",
    "消息",
    "表示",
    "称",
    "正在",
    "进一步",
    "成为",
    "相关",
    "推出",
    "发布",
    "开发",
    "升级",
    "整合",
    "agent",
    "copilot",
    "模型",
    "人工智能",
}

STORY_KIND_KEYWORDS = {
    "收购",
    "融资",
    "投资",
    "发布",
    "推出",
    "上线",
    "接入",
    "开发",
    "整合",
    "合作",
    "起诉",
    "指控",
    "禁用",
    "封禁",
    "监管",
    "财报",
    "agent",
    "copilot",
}

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
    "手机",
    "平板",
    "笔记本",
    "电视",
    "家电",
    "消费电子",
    "相机",
    "路由器",
    "蓝牙耳机",
    "智能手表",
    "智能手环",
}

TITLE_NEGATIVE_KEYWORDS = {
    "dlss",
    "路径追踪",
    "geforce",
    "玩家",
    "游戏",
    "早报",
    "晚报",
    "日报",
    "周报",
    "suv",
    "轿跑",
    "新车",
    "mg 4x",
    "mg 07",
}

REQUIRE_EXPLICIT_AI_SOURCES = {"IT之家", "36Kr AI", "The Verge", "Ars Technica"}

SOURCE_TITLE_BLACKLIST = {
    "IT之家": {
        "suv",
        "轿跑",
        "dlss",
        "游戏",
        "首发",
        "新车",
        "玩家",
        "早报",
        "晚报",
        "日报",
        "周报",
    },
    "36Kr AI": {"盘前", "股价", "航班", "晚报", "收盘", "开盘", "早报", "日报", "周报"},
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
article_time_cache = {}
results_lock = threading.Lock()


def clean_html(raw_html):
    text = re.sub(re.compile("<.*?>"), "", str(raw_html))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def strip_title_noise(text):
    cleaned = clean_html(text)
    for pattern in TITLE_NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_text(*parts):
    return " ".join(part for part in parts if part).lower()


def canonicalize_match_text(*parts):
    normalized = normalize_text(*(strip_title_noise(part) for part in parts if part))
    for source, target in MATCH_REPLACEMENTS:
        if re.fullmatch(r"[a-z0-9][a-z0-9\s.+#-]*", source):
            normalized = re.sub(
                rf"(?<![a-z0-9]){re.escape(source)}(?![a-z0-9])",
                f" {target} ",
                normalized,
            )
        else:
            normalized = normalized.replace(source, f" {target} ")

    for alias, target in sorted(ENTITY_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.fullmatch(r"[a-z0-9][a-z0-9\s.+#-]*", alias):
            normalized = re.sub(
                rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])",
                f" {target} ",
                normalized,
            )
        else:
            normalized = normalized.replace(alias, f" {target} ")

    normalized = re.sub(r"[“”\"'`‘’（）()【】\[\]<>《》]", " ", normalized)
    normalized = re.sub(r"[/|｜,:：;；!！?？]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def tokenize_ascii(text):
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9.+#-]{1,}", text.lower())
        if len(token) >= 2
    }


def tokenize_cjk_ngrams(text):
    normalized = re.sub(r"\s+", "", text)
    chunks = re.findall(r"[\u4e00-\u9fff]{2,}", normalized)
    grams = set()
    for chunk in chunks:
        upper = min(len(chunk), 12)
        for size in (2, 3):
            if upper < size:
                continue
            for idx in range(0, upper - size + 1):
                gram = chunk[idx : idx + size]
                if gram not in GENERIC_SIMILARITY_WORDS:
                    grams.add(gram)
    return grams


def extract_core_tokens(text):
    normalized = canonicalize_match_text(text)
    tokens = tokenize_ascii(normalized) | tokenize_cjk_ngrams(normalized)
    core_tokens = set()
    for token in tokens:
        if token.isdigit():
            continue
        if token in COMMON_ENTITY_TOKENS:
            continue
        if token in GENERIC_SIMILARITY_WORDS or token in EVENT_STOPWORDS:
            continue
        if len(token) < 2:
            continue
        core_tokens.add(token)
    return core_tokens


def extract_focus_tokens(text):
    focus_tokens = set()
    for token in extract_core_tokens(text):
        if token in STORY_KIND_KEYWORDS or token in POLICY_KEYWORDS:
            continue
        if len(token) < 3:
            continue
        focus_tokens.add(token)
    return focus_tokens


def build_title_core_text(title):
    return " ".join(sorted(extract_core_tokens(title)))


def build_similarity_signature(title, summary, original_title=""):
    title_text = strip_title_noise(title)
    summary_text = clean_html(summary)[:220]
    canonical_title = canonicalize_match_text(title_text)
    canonical_summary = canonicalize_match_text(summary_text)
    canonical_original_title = canonicalize_match_text(original_title)
    canonical_content = canonicalize_match_text(
        title_text, summary_text, original_title
    )
    title_tokens = tokenize_ascii(canonical_title) | tokenize_cjk_ngrams(canonical_title)
    body_tokens = (
        title_tokens
        | tokenize_ascii(canonical_summary)
        | tokenize_cjk_ngrams(canonical_summary)
        | tokenize_ascii(canonical_original_title)
        | tokenize_cjk_ngrams(canonical_original_title)
    )
    core_title_tokens = extract_core_tokens(title_text)
    core_body_tokens = (
        core_title_tokens
        | extract_core_tokens(summary_text)
        | extract_core_tokens(original_title)
    )
    focus_tokens = (
        extract_focus_tokens(title_text)
        | extract_focus_tokens(summary_text)
        | extract_focus_tokens(original_title)
    )
    strong_tokens = {
        token
        for token in core_body_tokens
        if len(token) >= 3
        and token not in GENERIC_SIMILARITY_WORDS
    }
    actor_tokens = {
        token
        for token in COMMON_ENTITY_TOKENS
        if keyword_matches(canonical_content, token)
    }
    policy_tokens = {
        token for token in POLICY_KEYWORDS if keyword_matches(canonical_content, token)
    }
    story_kind_tokens = {
        token
        for token in STORY_KIND_KEYWORDS
        if keyword_matches(canonical_content, token)
    }
    return {
        "title_tokens": title_tokens,
        "body_tokens": body_tokens,
        "strong_tokens": strong_tokens,
        "actor_tokens": actor_tokens,
        "policy_tokens": policy_tokens,
        "story_kind_tokens": story_kind_tokens,
        "title_core_tokens": core_title_tokens,
        "title_core_text": " ".join(sorted(core_title_tokens)),
        "focus_tokens": focus_tokens,
    }


def jaccard_similarity(left, right):
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def overlap_similarity(left, right):
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def sequence_similarity(left, right):
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def compute_item_value(item):
    age_hours = max(0.0, (now_bj.timestamp() - item["timestamp"]) / 3600)
    if age_hours <= 3:
        freshness_score = 25
    elif age_hours <= 6:
        freshness_score = 22
    elif age_hours <= 12:
        freshness_score = 17
    elif age_hours <= 18:
        freshness_score = 12
    else:
        freshness_score = 8

    actor_tokens = item["signature"]["actor_tokens"]
    story_kind_tokens = item["signature"]["story_kind_tokens"]
    focus_tokens = item["signature"]["focus_tokens"]
    content = normalize_text(item["title"], item["summary"], item["original_title"])

    story_level_score = 14
    if (
        len(actor_tokens & TOP_TIER_ACTORS) > 0
        and (
            story_kind_tokens & MAJOR_EVENT_KEYWORDS
            or has_any(content, STRATEGIC_PRODUCT_KEYWORDS)
        )
    ):
        story_level_score = 35
    elif story_kind_tokens & MAJOR_EVENT_KEYWORDS or has_any(
        content, STRATEGIC_PRODUCT_KEYWORDS
    ):
        story_level_score = 28
    elif item["relevance_score"] >= 5 or len(focus_tokens) >= 4:
        story_level_score = 22

    source_score = min(20, round(SOURCE_CREDIBILITY.get(item["source"], 5.0) * 2, 1))

    impact_score = 4
    if len(actor_tokens & TOP_TIER_ACTORS) > 0:
        impact_score += 3
    if has_any(content, HARDWARE_KEYWORDS | EMBODIED_KEYWORDS):
        impact_score += 1.5
    if has_any(content, POLICY_KEYWORDS):
        impact_score += 2
    if has_any(content, STRATEGIC_PRODUCT_KEYWORDS):
        impact_score += 2
    impact_score = min(10, impact_score)

    uniqueness_score = min(
        10,
        4
        + min(len(focus_tokens), 4)
        + min(len(item["signature"]["strong_tokens"]), 2),
    )

    item["score_breakdown"] = {
        "story_level": story_level_score,
        "freshness": freshness_score,
        "source": source_score,
        "impact": impact_score,
        "uniqueness": uniqueness_score,
    }
    return (
        story_level_score
        + freshness_score
        + source_score
        + impact_score
        + uniqueness_score
    )


def are_likely_duplicates(left, right):
    shared_strong_tokens = (
        left["signature"]["strong_tokens"] & right["signature"]["strong_tokens"]
    )
    shared_actor_tokens = (
        left["signature"]["actor_tokens"] & right["signature"]["actor_tokens"]
    )
    shared_policy_tokens = (
        left["signature"]["policy_tokens"] & right["signature"]["policy_tokens"]
    )
    shared_story_kind_tokens = (
        left["signature"]["story_kind_tokens"] & right["signature"]["story_kind_tokens"]
    )
    shared_title_core_tokens = (
        left["signature"]["title_core_tokens"] & right["signature"]["title_core_tokens"]
    )
    shared_focus_tokens = left["signature"]["focus_tokens"] & right["signature"]["focus_tokens"]
    title_similarity = jaccard_similarity(
        left["signature"]["title_tokens"], right["signature"]["title_tokens"]
    )
    body_similarity = jaccard_similarity(
        left["signature"]["body_tokens"], right["signature"]["body_tokens"]
    )
    title_core_overlap = overlap_similarity(
        left["signature"]["title_core_tokens"], right["signature"]["title_core_tokens"]
    )
    title_core_similarity = sequence_similarity(
        left["signature"]["title_core_text"], right["signature"]["title_core_text"]
    )
    if left["link"].strip().lower() == right["link"].strip().lower():
        return True
    if (
        shared_actor_tokens
        and shared_title_core_tokens
        and (
            title_core_overlap >= 0.72
            or title_core_similarity >= 0.72
            or (shared_story_kind_tokens and title_core_overlap >= 0.5)
        )
    ):
        return True
    if (
        shared_actor_tokens
        and len(shared_focus_tokens) >= 2
        and (
            shared_story_kind_tokens
            or body_similarity >= 0.18
            or title_core_similarity >= 0.62
            or title_core_overlap >= 0.34
        )
    ):
        return True
    if (
        shared_actor_tokens
        and len(shared_focus_tokens) >= 1
        and shared_story_kind_tokens
        and (title_core_overlap >= 0.45 or title_core_similarity >= 0.58)
    ):
        return True
    if (
        shared_actor_tokens
        and shared_strong_tokens
        and len(shared_focus_tokens) >= 1
        and (title_similarity >= 0.28 or body_similarity >= 0.24)
    ):
        return True
    if len(shared_strong_tokens) >= 2 and (
        title_similarity >= 0.16
        or body_similarity >= 0.16
        or title_core_overlap >= 0.5
    ):
        return True
    if (
        len(shared_strong_tokens) >= 1
        and title_similarity >= 0.38
        and body_similarity >= 0.22
    ):
        return True
    if (
        len(shared_title_core_tokens) >= 2
        and title_core_overlap >= 0.8
        and (shared_actor_tokens or shared_story_kind_tokens)
    ):
        return True
    if body_similarity >= 0.68:
        return True
    return False


def deduplicate_results(items):
    selected = []
    for item in sorted(
        items,
        key=lambda current: (current["value_score"], current["timestamp"]),
        reverse=True,
    ):
        if any(are_likely_duplicates(item, existing) for existing in selected):
            continue
        selected.append(item)
    return selected


def dominant_actor(item):
    actor_tokens = sorted(item["signature"]["actor_tokens"] & TOP_TIER_ACTORS)
    if actor_tokens:
        return actor_tokens[0]
    actor_tokens = sorted(item["signature"]["actor_tokens"])
    if actor_tokens:
        return actor_tokens[0]
    return ""


def distribute_category_items(items, limit):
    remaining = list(items)
    selected = []
    streak_actor = ""
    streak_count = 0

    while remaining and len(selected) < limit:
        chosen_index = None
        for index, item in enumerate(remaining):
            actor = item.get("dominant_actor", "")
            if actor and actor == streak_actor and streak_count >= MAX_CONSECUTIVE_SAME_ACTOR:
                continue
            chosen_index = index
            break

        if chosen_index is None:
            chosen_index = 0

        chosen = remaining.pop(chosen_index)
        actor = chosen.get("dominant_actor", "")
        if actor and actor == streak_actor:
            streak_count += 1
        else:
            streak_actor = actor
            streak_count = 1 if actor else 0
        selected.append(chosen)

    return selected


def keyword_matches(text, keyword):
    if re.fullmatch(r"[a-z0-9][a-z0-9\s.+#-]*", keyword):
        pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"
        return re.search(pattern, text) is not None
    return keyword in text


def has_any(text, keywords):
    return any(keyword_matches(text, keyword) for keyword in keywords)


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


def has_explicit_ai_signal_in_title(title):
    title_text = normalize_text(title)
    return has_any(
        title_text, PRIMARY_AI_KEYWORDS | HARDWARE_KEYWORDS | EMBODIED_KEYWORDS
    )


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
    content = normalize_text(title, summary)
    if not has_any(
        content, PRIMARY_AI_KEYWORDS | HARDWARE_KEYWORDS | EMBODIED_KEYWORDS
    ):
        return False
    score = ai_relevance_score(title, summary)
    threshold = 4 if strict else 2
    if min_score is not None:
        threshold = max(threshold, min_score)
    if (
        source_name in REQUIRE_EXPLICIT_AI_SOURCES
        and not has_explicit_ai_signal_in_title(title)
    ):
        return False
    return score >= threshold


def summarize_text(summary, limit=100):
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


def fetch_aibase_article_datetime(link, headers=None):
    if link in article_time_cache:
        return article_time_cache[link]

    request_headers = headers or {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(link, headers=request_headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        match = re.search(
            r"发布时间\s*[:：]\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})[号日]\s*(\d{1,2}):(\d{2})",
            text,
        )
        if match:
            dt_bj = beijing_tz.localize(
                datetime(
                    int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                    int(match.group(4)),
                    int(match.group(5)),
                )
            )
            article_time_cache[link] = dt_bj
            return dt_bj
    except Exception:
        pass

    article_time_cache[link] = None
    return None


def add_result(config, title, link, dt_bj, summary):
    normalized_title = strip_title_noise(title)
    unique_key = link.strip().lower()
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

    with results_lock:
        if unique_key in seen_keys:
            return
        seen_keys.add(unique_key)

    display_title = normalized_title
    display_summary = summarize_text(summary)
    if config["lang"] == "en":
        display_title = translate_text(display_title)
        if display_summary:
            display_summary = summarize_text(translate_text(display_summary), limit=100)

    relevance_score = ai_relevance_score(title, summary)
    signature = build_similarity_signature(
        display_title,
        display_summary or summary,
        original_title=normalized_title if config["lang"] == "en" else "",
    )
    item = {
        "source": config["name"],
        "title": display_title,
        "original_title": normalized_title if config["lang"] == "en" else "",
        "link": link,
        "time": dt_bj.strftime('%m-%d %H:%M'),
        "timestamp": dt_bj.timestamp(),
        "summary": display_summary,
        "relevance_score": relevance_score,
        "signature": signature,
    }
    item["value_score"] = compute_item_value(item)
    item["dominant_actor"] = dominant_actor(item)

    with results_lock:
        results.append(item)


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
            article_dt_bj = fetch_aibase_article_datetime(link, headers=headers)
            if article_dt_bj is not None:
                dt_bj = article_dt_bj
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


def score_video_topic(item):
    content = normalize_text(item["title"], item["summary"], item["original_title"])
    score = 45
    if has_any(content, {"对标", "瞄准", "争议", "冲突", "起诉", "指控", "封禁", "叫板", "威胁"}):
        score += 20
    if has_any(content, {"openai", "google", "anthropic", "microsoft", "meta", "nvidia", "chatgpt", "gemini", "claude", "deepseek"}):
        score += 15
    if has_any(content, {"发布", "推出", "上线", "升级", "模型", "codex", "agent", "芯片", "眼镜", "机器人", "用户", "融资", "收购"}):
        score += 12
    if has_any(content, {"全球", "10亿", "百亿", "用户", "周活跃", "女性", "工作", "浏览器", "照片"}):
        score += 10
    if has_any(content, {"财报", "估值", "ipo", "监管", "法案", "法规"}):
        score += 8
    if len(item["summary"]) >= 80:
        score += 5
    return min(score, 100)


def video_star_rating(score):
    if score >= 90:
        return "★★★★★"
    if score >= 80:
        return "★★★★☆"
    if score >= 70:
        return "★★★☆☆"
    if score >= 60:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def video_reason(item):
    content = normalize_text(item["title"], item["summary"], item["original_title"])
    if has_any(content, {"瞄准", "争议", "起诉", "指控", "威胁", "对标"}):
        return "冲突感强"
    if has_any(content, {"10亿", "全球", "周活跃", "百亿", "用户"}):
        return "大众感知强"
    if has_any(content, {"融资", "收购", "估值", "ipo"}):
        return "资本话题强"
    if has_any(content, {"眼镜", "机器人", "照片", "浏览器"}):
        return "画面感强"
    if has_any(content, {"发布", "推出", "升级", "模型", "codex", "agent"}):
        return "产品爆点强"
    return "讨论空间大"


def video_direction(item):
    content = normalize_text(item["title"], item["summary"], item["original_title"])
    if has_any(content, {"瞄准", "争议", "起诉", "指控", "对标"}):
        return "冲突解读"
    if has_any(content, {"融资", "收购", "估值", "ipo", "监管"}):
        return "趋势拆解"
    if has_any(content, {"眼镜", "机器人", "照片"}):
        return "画面切入"
    if has_any(content, {"用户", "全球", "周活跃", "工作"}):
        return "大众影响"
    return "产品解读"


def build_html(categories):
    total_items = sum(len(cat_data["items"]) for cat_data in categories.values())
    version = "v1.0.5"
    active_categories = [
        (cat_name, cat_data)
        for cat_name, cat_data in categories.items()
        if cat_data["items"]
    ]
    all_items = []
    for _, cat_data in active_categories:
        all_items.extend(cat_data["items"])
    video_candidates = []
    for item in all_items:
        score = score_video_topic(item)
        video_candidates.append(
            {
                "title": item["title"],
                "source": item["source"],
                "link": item["link"],
                "score": score,
                "stars": video_star_rating(score),
                "reason": video_reason(item),
                "direction": video_direction(item),
            }
        )
    video_candidates.sort(key=lambda item: (item["score"], item["title"]), reverse=True)
    top_video_topics = video_candidates[:5]
    category_labels = {
        "大模型与前沿技术": "大模型与前沿",
        "AI算力与硬件芯片": "AI算力与芯片",
        "具身智能与智能终端": "具身智能与终端",
        "政策风向与投融资": "政策与投融资",
        "综合前沿资讯": "综合资讯",
    }

    html_parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "    <title>AI 行业 24 小时精选快讯</title>",
        "    <style>",
        "        @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;500;700;800&family=Nunito:wght@600;700;800&family=Noto+Sans+SC:wght@400;500;700;800&display=swap');",
        "        :root { --mint: #19c8b9; --mint-soft: #e6f9f6; --leaf: #6fba2c; --sun: #f5c31c; --soil: #794f27; --soil-soft: #9f927d; --cream: #f8f8f0; --cream-deep: #f0e8d8; --paper: #fbfaf4; --line: #c4b89e; --line-strong: #a89878; --shadow: 0 4px 0 rgba(196, 184, 158, 0.98); --shadow-soft: 0 18px 40px -28px rgba(61, 52, 40, 0.22); --radius-xl: 28px; --radius-lg: 24px; --radius-md: 20px; --radius-pill: 999px; --page-gutter: clamp(16px, 2vw, 28px); --page-block: clamp(18px, 3vw, 32px); --hero-title: clamp(2.2rem, 5vw, 4rem); --content-max-width: 1900px; }",
        "        * { box-sizing: border-box; }",
        "        html { scroll-behavior: smooth; }",
        "        body { margin: 0; font-family: 'Noto Sans SC', 'M PLUS Rounded 1c', sans-serif; color: var(--soil); background: radial-gradient(circle at top, rgba(245, 195, 28, 0.16), transparent 24%), radial-gradient(circle at left 14%, rgba(111, 186, 44, 0.12), transparent 20%), linear-gradient(180deg, #f8f8f0 0%, #f5f1e6 38%, #f3eedf 100%); }",
        "        body::before { content: ''; position: fixed; inset: 0; pointer-events: none; opacity: 0.22; background-image: radial-gradient(rgba(121, 79, 39, 0.11) 1px, transparent 1px); background-size: 18px 18px; }",
        "        a { color: inherit; }",
        "        .page-shell { position: relative; width: min(100%, var(--content-max-width)); margin: 0 auto; padding: var(--page-block) var(--page-gutter) 40px; }",
        "        .hero-panel,.score-panel,.nav-shell,.cat-panel,.footer-panel { position: relative; background: rgba(251,250,244,.96); border: 3px solid var(--line); box-shadow: var(--shadow), var(--shadow-soft); }",
        "        .hero-panel { overflow: hidden; padding: 14px 18px 12px; border-radius: 28px; }",
        "        .hero-panel::before { content: ''; position: absolute; width: 240px; height: 240px; right: -60px; top: -80px; border-radius: 48% 52% 44% 56%; background: radial-gradient(circle, rgba(25, 200, 185, 0.16) 0%, rgba(25, 200, 185, 0) 70%); }",
        "        .hero-panel::after { content: ''; position: absolute; width: 180px; height: 180px; left: -50px; bottom: -70px; border-radius: 50%; background: radial-gradient(circle, rgba(245, 195, 28, 0.12) 0%, rgba(245, 195, 28, 0) 72%); }",
        "        .hero-kicker { display: inline-flex; align-items: center; gap: 8px; padding: 10px 16px; border-radius: var(--radius-pill); background: var(--mint-soft); border: 2px solid rgba(25, 200, 185, 0.22); font-family: 'Nunito', sans-serif; font-size: 0.86rem; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase; color: #158879; }",
        "        .hero-grid { position: relative; z-index: 1; display: grid; grid-template-columns: minmax(0,1fr) auto; gap: 14px; align-items: center; }",
        "        .hero-main{display:flex;align-items:center;gap:12px;min-width:0}",
        "        .hero-title { margin: 0; font-family: 'Nunito', 'Noto Sans SC', sans-serif; font-size: clamp(1.35rem, 2.6vw, 2rem); line-height: 1; letter-spacing: -0.03em; color: var(--soil); white-space: nowrap; }",
        "        .hero-copy { margin: 0; max-width: none; font-size: 0.88rem; line-height: 1.45; color: var(--soil-soft); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
        "        .stats-grid { display: flex; gap: 10px; align-content: center; }",
        "        .stat-card { padding: 8px 12px; border-radius: 18px; border: 2px solid var(--line); background: linear-gradient(180deg, rgba(248,248,240,0.98), rgba(240,232,216,0.94)); box-shadow: 0 3px 0 rgba(196, 184, 158, 0.98); min-height: 0; min-width: 160px; }",
        "        .stat-label { font-size: 0.68rem; color: var(--soil-soft); line-height: 1.2; }",
        "        .stat-value { margin-top: 4px; font-family: 'Nunito', 'Noto Sans SC', sans-serif; font-size: 0.88rem; font-weight: 800; color: var(--soil); line-height: 1.25; }",
        "        .hero-divider { position: relative; z-index: 1; margin-top: 10px; height: 10px; border-radius: 999px; background: repeating-linear-gradient(90deg, rgba(196, 184, 158, 0.72) 0 12px, rgba(240, 232, 216, 0.95) 12px 24px); opacity: 1; }",
        "        .score-panel{margin:16px 0;padding:16px;border-radius:28px;background:linear-gradient(180deg, rgba(251,250,244,.98), rgba(240,232,216,.92))}.score-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;padding-bottom:10px;border-bottom:2px dashed rgba(164,143,114,.28)}.score-title{margin:0;font-family:'Nunito','Noto Sans SC',sans-serif;font-size:1rem;color:var(--soil)}.score-note{font-size:.82rem;color:var(--soil-soft)}.score-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}",
        "        .topic-card{padding:14px;border-radius:22px;border:2px solid rgba(196,184,158,.92);background:linear-gradient(180deg, rgba(251,250,244,.98), rgba(248,248,240,.98));box-shadow:0 3px 0 rgba(196,184,158,.98)}.topic-rank{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:12px;background:linear-gradient(180deg,#fff3bf,#f7d768);border:2px solid rgba(164,143,114,.52);font-family:'Nunito',sans-serif;font-weight:800;color:var(--soil);box-shadow:0 3px 0 rgba(219,169,14,.45)}.source-pill{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:var(--mint-soft);border:2px solid rgba(25,200,185,.18);font-size:.75rem;font-weight:800;color:#158879}.topic-stars{margin-top:10px;font-size:.92rem;font-weight:800;color:#5f962e;letter-spacing:.05em}.topic-title{margin:10px 0 0;font-size:.95rem;line-height:1.55;font-weight:800;color:var(--soil);display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}.topic-title a{text-decoration:none;color:inherit}.topic-meta{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}.topic-chip{padding:8px 10px;border-radius:16px;background:rgba(122,83,48,.06);border:1px solid rgba(196,184,158,.88)}.chip-label{font-size:.68rem;color:var(--soil-soft)}.chip-value{margin-top:4px;font-size:.82rem;font-weight:800;color:var(--soil)}",
        "        .nav-shell { position: sticky; top: 10px; z-index: 20; margin: 18px 0 26px; padding: 12px; border-radius: 28px; overflow-x: auto; background: rgba(248, 248, 240, 0.96); }",
        "        .nav-shell::-webkit-scrollbar { display: none; }",
        "        .nav-shell { -ms-overflow-style: none; scrollbar-width: none; }",
        "        .nav-track { display: flex; gap: 10px; flex-wrap: nowrap; min-width: max-content; }",
        "        .cat-btn { display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 18px; border: 2px solid var(--line); border-radius: var(--radius-pill); background: var(--paper); color: var(--soil-soft); font-family: 'Nunito', 'Noto Sans SC', sans-serif; font-size: 0.92rem; font-weight: 800; cursor: pointer; box-shadow: 0 3px 0 rgba(196, 184, 158, 0.98); transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease, color 0.18s ease; white-space: nowrap; }",
        "        .cat-btn:hover { transform: translateY(-1px); border-color: var(--line-strong); box-shadow: 0 4px 0 rgba(164, 143, 114, 0.95); }",
        "        .cat-btn.is-active { color: var(--soil); border-color: rgba(25, 200, 185, 0.32); background: linear-gradient(180deg, var(--mint-soft), #f7fffd); box-shadow: 0 4px 0 rgba(25, 200, 185, 0.38); }",
        "        .cat-count { display: inline-flex; min-width: 28px; height: 28px; align-items: center; justify-content: center; padding: 0 8px; border-radius: 999px; background: rgba(122, 83, 48, 0.08); color: var(--soil); font-size: 0.76rem; }",
        "        .category-grid { display: grid; gap: 18px; grid-template-columns: repeat(1,minmax(0,1fr)); align-items: start; }",
        "        .category-grid.single-focus { display:block; width:100%; } .category-grid.single-focus .cat-panel { display:block; width:100%; min-width:100%; max-width:none; justify-self:stretch; } .category-grid.single-focus .news-list{display:flex;flex-direction:column;gap:12px;align-items:stretch}.category-grid.single-focus .news-card{width:100%;min-height:0;padding:16px 18px;border-radius:24px;border-color:rgba(25,200,185,.28);box-shadow:0 3px 0 rgba(25,200,185,.18);align-items:flex-start}.category-grid.single-focus .news-rank{width:38px;height:38px;flex:0 0 38px;border-radius:14px;margin-top:2px}.category-grid.single-focus .news-body{display:flex;flex-direction:column;gap:6px}.category-grid.single-focus .meta-row{justify-content:flex-start;align-items:center;gap:12px}.category-grid.single-focus .time-stamp{margin-left:auto;white-space:nowrap}.category-grid.single-focus .news-title{-webkit-line-clamp:1;font-size:1rem;line-height:1.45;margin-top:2px}.category-grid.single-focus .en-subtitle{display:block;margin-top:0;font-size:.78rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.category-grid.single-focus .summary-compact{-webkit-line-clamp:1;margin-top:0;font-size:.84rem;line-height:1.6}",
        "        .cat-panel { padding: 16px; border-radius: 30px; scroll-margin-top: 104px; background: linear-gradient(180deg, rgba(251, 250, 244, 0.98), rgba(240, 232, 216, 0.9)); }",
        "        .section-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; padding-bottom: 14px; border-bottom: 2px dashed rgba(164, 143, 114, 0.28); }",
        "        .section-icon { display: inline-flex; align-items: center; justify-content: center; width: 52px; height: 52px; border-radius: 18px; background: linear-gradient(180deg, #fff7df, #f5deb7); border: 2px solid var(--line); box-shadow: 0 3px 0 rgba(205, 187, 159, 0.95); font-size: 1.35rem; }",
        "        .section-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }",
        "        .section-title { margin: 0; font-family: 'Nunito', 'Noto Sans SC', sans-serif; font-size: 1.1rem; line-height: 1.2; color: var(--soil); }",
        "        .section-subtitle { margin-top: 4px; font-size: 0.82rem; color: var(--soil-soft); }",
        "        .section-count { display: inline-flex; align-items: center; justify-content: center; min-width: 42px; height: 32px; padding: 0 10px; border-radius: 999px; background: rgba(111, 186, 44, 0.14); border: 2px solid rgba(111, 186, 44, 0.14); font-size: 0.8rem; font-weight: 800; color: #5f962e; }",
        "        .news-list { display: flex; flex-direction: column; gap: 12px; }",
        "        .news-card { display: flex; gap: 12px; padding: 14px; border-radius: 22px; border: 2px solid rgba(196, 184, 158, 0.92); background: linear-gradient(180deg, rgba(251,250,244,0.98), rgba(248,248,240,0.98)); box-shadow: 0 3px 0 rgba(196, 184, 158, 0.98); transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease; min-width: 0; }",
        "        .news-card:hover { transform: translateY(-2px); border-color: rgba(25, 200, 185, 0.38); box-shadow: 0 4px 0 rgba(25, 200, 185, 0.34), 0 18px 32px -26px rgba(122, 83, 48, 0.38); }",
        "        .news-rank { display: inline-flex; align-items: center; justify-content: center; width: 38px; height: 38px; flex: 0 0 38px; border-radius: 16px; background: linear-gradient(180deg, #fff3bf, #f7d768); border: 2px solid rgba(164, 143, 114, 0.52); font-family: 'Nunito', sans-serif; font-weight: 800; color: var(--soil); box-shadow: 0 3px 0 rgba(219, 169, 14, 0.45); }",
        "        .news-body { min-width: 0; flex: 1; }",
        "        .meta-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }",
        "        .source-pill { display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border-radius: 999px; background: var(--mint-soft); border: 2px solid rgba(25, 200, 185, 0.18); font-size: 0.75rem; font-weight: 800; color: #158879; }",
        "        .time-stamp { font-size: 0.78rem; color: var(--soil-soft); }",
        "        .news-title { margin: 10px 0 0; font-size: 1rem; line-height: 1.55; font-weight: 800; color: var(--soil); display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }",
        "        .news-title a { text-decoration: none; }",
        "        .news-title a:hover { color: #158879; }",
        "        .en-subtitle { margin-top: 6px; font-size: 0.75rem; color: var(--soil-soft); font-family: 'M PLUS Rounded 1c', sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
        "        .summary-compact { margin: 8px 0 0; font-size: 0.86rem; line-height: 1.7; color: #82664a; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 3; overflow: hidden; }",
        "        .footer-panel { margin-top: 28px; padding: 18px 20px; border-radius: 28px; text-align: center; color: var(--soil-soft); font-size: 0.88rem; }",
        "        .hidden-section { display: none !important; }",
        "        @media (min-width:760px){.category-grid.cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}} @media (min-width:1120px){.category-grid.cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}} @media (min-width:1460px){.category-grid.cols-4{grid-template-columns:repeat(4,minmax(0,1fr))}} @media (min-width:1780px){.category-grid.cols-5{grid-template-columns:repeat(5,minmax(0,1fr))}}",
        "        @media (max-width: 1180px) { .hero-grid { grid-template-columns: 1fr; } .hero-main{display:block} .hero-copy{margin-top:6px;white-space:normal} .stats-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); } }",
        "        @media (max-width: 980px) { .category-grid.single-focus { grid-template-columns: 1fr; } .category-grid.single-focus .news-list{display:flex;flex-direction:column;} }",
        "        @media (max-width:1200px){.score-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-copy{white-space:normal}} @media (max-width:640px) { .page-shell { padding-inline: 12px; } .nav-track { flex-wrap: nowrap; } .stats-grid { grid-template-columns: 1fr; } .hero-panel { padding: 20px; } .news-card { padding: 12px; } .section-icon { width: 46px; height: 46px; } .stat-card { min-height: unset; } .score-grid{grid-template-columns:1fr}.topic-meta{grid-template-columns:1fr} }",
        "    </style>",
        "</head>",
        "<body>",
        '    <div class="page-shell">',
        '        <header class="hero-panel"><div class="hero-grid"><div class="hero-main"><h1 class="hero-title">AI 日报</h1><p class="hero-copy">过去 24 小时 AI 动态按主题整理，优先保留模型、算力、具身智能与行业趋势相关事件。</p></div><div class="stats-grid">',
        f'                    <div class="stat-card"><div class="stat-label">日期</div><div class="stat-value">{now_bj.strftime("%Y年%m月%d日")}</div></div>',
        f'                    <div class="stat-card"><div class="stat-label">新闻条数</div><div class="stat-value">{total_items} 条</div></div>',
        f'                    <div class="stat-card"><div class="stat-label">刷新时间</div><div class="stat-value">{now_bj.strftime("%Y-%m-%d %H:%M")}</div></div>',
        '                </div></div><div class="hero-divider"></div></header>',
        '        <section class="score-panel"><div class="score-head"><h2 class="score-title">短视频选题评分</h2><div class="score-note">按爆款潜力从高到低</div></div><div class="score-grid">',
    ]

    for idx, topic in enumerate(top_video_topics, 1):
        html_parts.append(
            f'<article class="topic-card"><div class="meta-row"><span class="topic-rank">{idx}</span><span class="source-pill">{html.escape(topic["source"])}</span></div><div class="topic-stars">{topic["stars"]}</div><h3 class="topic-title"><a href="{html.escape(topic["link"])}" target="_blank" rel="noopener noreferrer">{html.escape(topic["title"])}</a></h3><div class="topic-meta"><div class="topic-chip"><div class="chip-label">理由</div><div class="chip-value">{html.escape(topic["reason"])}</div></div><div class="topic-chip"><div class="chip-label">建议方向</div><div class="chip-value">{html.escape(topic["direction"])}</div></div></div></article>'
        )

    html_parts.extend(
        [
            "</div></section>",
            '        <nav class="nav-shell"><div class="nav-track"><button onclick="filterCategory(\'all\', this)" class="cat-btn is-active">全部分类 <span class="cat-count">ALL</span></button>',
        ]
    )

    for cat_name, cat_data in active_categories:
        html_parts.append(
            f'<button onclick="filterCategory(\'{cat_data["id"]}\', this)" class="cat-btn">{cat_data["icon"]} {html.escape(category_labels.get(cat_name, cat_name))} <span class="cat-count">{len(cat_data["items"])}</span></button>'
        )

    grid_cols = min(max(len(active_categories), 1), 5)
    html_parts.append(
        f'</div></nav><main id="news-container"><div id="category-grid" class="category-grid cols-{grid_cols}">'
    )

    for cat_name, cat_data in active_categories:
        items = cat_data["items"]
        html_parts.append(
            f'<section id="{cat_data["id"]}" class="cat-section cat-panel" data-title-length="{len(cat_name)}">'
        )
        html_parts.append(
            f'<div class="section-head"><span class="section-icon">{cat_data["icon"]}</span><div class="news-body"><div class="section-title-row"><h2 class="section-title">{cat_name}</h2><span class="section-count">{len(items)} 条</span></div><div class="section-subtitle">精选动态</div></div></div>'
        )
        html_parts.append('<div class="news-list">')
        for idx, item in enumerate(items, 1):
            summary = item["summary"]
            if summary.startswith("IT之家"):
                summary = summary.split("消息，", 1)[-1].strip()
            subtitle_html = (
                f'<div class="en-subtitle">{html.escape(item["original_title"])} </div>'
                if item.get("original_title")
                else ""
            )
            html_parts.append(
                f'<article class="news-card"><div class="news-rank">{idx}</div><div class="news-body"><div class="meta-row"><span class="source-pill">{html.escape(item["source"])}</span><time class="time-stamp">{html.escape(item["time"])}</time></div><h3 class="news-title"><a href="{html.escape(item["link"])}" target="_blank" rel="noopener noreferrer">{html.escape(item["title"])}</a></h3>{subtitle_html}<p class="summary-compact">{html.escape(summary)}</p></div></article>'
            )
        html_parts.append("</div></section>")

    html_parts.extend(
        [
            "</div></main>",
            f'        <footer class="footer-panel">{version}</footer>',
            "    </div>",
            "    <script>",
            "        function syncCategoryLayout(catId) {",
            "            const grid = document.getElementById('category-grid');",
            "            if (!grid) return;",
            "            const visibleSections = Array.from(document.querySelectorAll('.cat-section')).filter(sec => !sec.classList.contains('hidden-section'));",
            "            const isSingleFocus = catId !== 'all' && visibleSections.length === 1;",
            "            grid.classList.toggle('single-focus', isSingleFocus);",
            "            if (!isSingleFocus) return;",
            "        }",
            "        function filterCategory(catId, btnElement) {",
            "            document.querySelectorAll('.cat-btn').forEach(btn => btn.classList.remove('is-active'));",
            "            btnElement.classList.add('is-active');",
            "            document.querySelectorAll('.cat-section').forEach(sec => {",
            "                if (catId === 'all' || sec.id === catId) {",
            "                    sec.classList.remove('hidden-section');",
            "                } else {",
            "                    sec.classList.add('hidden-section');",
            "                }",
            "            });",
            "            syncCategoryLayout(catId);",
            "            if (catId !== 'all') { document.getElementById(catId).scrollIntoView({ behavior: 'smooth', block: 'start' }); }",
            "        }",
            "        syncCategoryLayout('all');",
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

results = deduplicate_results(results)
results.sort(key=lambda item: (item["value_score"], item["timestamp"]), reverse=True)
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
    categories[category]["items"].append(item)

for category in categories.values():
    category["items"] = distribute_category_items(
        category["items"], MAX_ITEMS_PER_CATEGORY
    )

save_dir = os.path.expanduser(
    os.environ.get("AI_DAILY_NEWS_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
)
os.makedirs(save_dir, exist_ok=True)
date_str = now_bj.strftime("%Y%m%d")
output_path = os.path.join(save_dir, f"AI_Daily_News_{date_str}.html")
with open(output_path, "w", encoding="utf-8") as file:
    file.write(build_html(categories))

print(f"📝 网页生成成功: {output_path}")
