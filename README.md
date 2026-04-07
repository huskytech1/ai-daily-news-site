# AI Daily News Site

自动抓取并生成 AI 日报静态页面，适合接入 GitHub Actions + Netlify。

## 自动更新

- GitHub Actions 每天北京时间 08:00 自动运行一次
- 输出目录固定为 `site/`
- `site/index.html` 始终是最新首页
- `site/AI_Daily_News_YYYYMMDD.html` 保留日期归档

## 本地运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
AI_DAILY_NEWS_OUTPUT_DIR="site" python scripts/main.py
cp site/AI_Daily_News_*.html site/index.html
```

## Netlify

- 仓库内已包含 `netlify.toml`
- Netlify 导入仓库后，发布目录使用 `site`
- 之后 GitHub Actions 推送新内容时，Netlify 会自动重新部署

## 说明

- 主要抓取逻辑在 `scripts/main.py`
- 定时任务在 `.github/workflows/daily-update.yml`
- 输出站点在 `site/`
