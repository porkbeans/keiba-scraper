import logging
from typing import Optional

import scrapy
from scrapy.crawler import Crawler
from scrapy.signals import engine_stopped
from selenium import webdriver

logger = logging.getLogger(__name__)


class SeleniumDownloaderMiddleware:
    _driver: Optional[webdriver.Chrome] = None

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            cls._driver = webdriver.Chrome(options=options)

        return cls._driver

    @classmethod
    def from_crawler(cls, crawler: Crawler):
        crawler.signals.connect(cls.closed, engine_stopped)
        return cls()

    @classmethod
    def closed(cls):
        if cls._driver is not None:
            cls._driver.quit()

    def process_request(self, request: scrapy.Request, spider):
        if request.method != 'GET':
            return None
        else:
            driver = self.get_driver()

            driver.get(request.url)
            body = driver.page_source.encode('utf-8')

            return scrapy.http.TextResponse(url=request.url, body=body, encoding='utf-8')

    @staticmethod
    def process_response(request, response, spider):
        return response

    @staticmethod
    def process_exception(request, exception, spider):
        return None
