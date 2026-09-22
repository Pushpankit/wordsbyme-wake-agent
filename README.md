# WordsByMe Wake Agent

Scheduled Python crawler for WordsByMe.

GitHub Actions starts one crawl every 5 minutes, so your laptop and VS Code do not need to stay on.

## Files

- `agent.py` — performs one crawl and exits.
- `requirements.txt` — Python dependencies.
- `.github/workflows/crawl.yml` — GitHub Actions schedule.

## Important

This keeps making HTTP requests to your site. It does not control Googlebot and does not guarantee Google indexing. GitHub scheduled workflows can also be delayed during periods of high Actions load.
