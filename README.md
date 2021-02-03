# keiba-scraper

Scraper for horse race data.

# Usage

```bash
# Pull the image
docker pull porkbeans/keiba-scraper:latest

# Run spider
docker run -it --rm porkbeans/keiba-scraper:latest scrapy crawl NetkeibaRaceSpider
```
