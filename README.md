# AI Daily News Site

自动抓取并生成 AI 日报静态页面，适合接入 GitHub Actions + GitHub Pages。

## 自动更新

- GitHub Actions 在每个工作日北京时间 09:27 自动运行一次
- 输出目录固定为 `site/`
- `site/index.html` 始终是最新首页
- `site/AI_Daily_News_YYYYMMDD.html` 保留日期归档
- 站点通过 GitHub Pages 部署，不再依赖本地定时器或 Netlify 回推

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
AI_DAILY_NEWS_OUTPUT_DIR="site" python scripts/main.py
cp site/AI_Daily_News_*.html site/index.html
```

## 说明

- 主要抓取逻辑在 `scripts/main.py`
- 定时任务在 `.github/workflows/daily-update.yml`
- 输出站点在 `site/`
- 线上部署地址为 `https://huskytech1.github.io/ai-daily-news-site/`
