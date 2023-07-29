#!/usr/bin/env python

import asyncio
import datetime
import typing
import json
import urllib.parse

import bs4
import httpx

import structlog
import msgpack

from crawler.models import (
    CrawlResult,
    Link
)
from crawler.queue_processors import QueueProcessor

import recipe_scrapers


logger = structlog.getLogger()


CRAWL_RECENCY_PERIOD = 60 * 60 * 24 * 7


class HTMLParser(QueueProcessor):
    read_topic = "crawl-results"
    client: typing.Optional[httpx.AsyncClient] = None
    group_id = "parse-crawl-results"

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=30
        )

    def decode_message(self, message: bytes) -> CrawlResult:
        return CrawlResult(**msgpack.unpackb(message))

    def has_link_been_visited_recently(self, url: str) -> bool:
        if self.cache.get(f"visited__{url}"):
            return True
        self.cache.set(f"visited__{url}", 1, ex=CRAWL_RECENCY_PERIOD)
        return False

    def is_url_nofollow(self, url: str, crawl_result: CrawlResult):
        return url == crawl_result.url

    def get_links(self, crawl_result: CrawlResult) -> typing.Generator[Link, None, None]:
        soup = bs4.BeautifulSoup(crawl_result.contents.decode('utf-8'))
        for anchor in soup.find_all("a"):
            url = anchor.get('href', None)
            if not url:
                continue
            url = urllib.parse.urljoin(crawl_result.url, url)
            if self.is_url_nofollow(url, crawl_result):
                continue
            if self.has_link_been_visited_recently(url):
                continue
            yield Link(url=url, metadata={'referrer': crawl_result.url})

    async def process_message(self, crawl_result: CrawlResult):
        logger.debug("Processing message...", url=crawl_result.url)
        try:
            contents = crawl_result.contents.decode('utf-8')
        except UnicodeError:
            logger.error(f"Crawl for {crawl_result.url} yielded non-utf8 contents.")
            return
        else:
            try:
                logger.debug("Trying to scrape recipe:", url=crawl_result.url)
                scraped = recipe_scrapers.scrape_html(contents)
            except recipe_scrapers.NoSchemaFoundInWildMode as exc:
                logger.error(
                    f"(Likely unsupported recipe site) Could not make sense of \"{crawl_result.url}\"",
                    url=exc.url,
                    message=exc.message
                )
            else:
                scraped_contents = json.dumps(scraped.to_json())
                logger.info("Found recipe:", recipe=scraped.to_json(), url=crawl_result.url)
                await self.producer.send('recipes', scraped_contents.encode('utf-8'))
                for link in self.get_links(crawl_result):
                    await self.producer.send('links', link.model_dump_json().encode('utf-8'))


def main():
    crawler = HTMLParser()
    asyncio.get_event_loop().run_until_complete(crawler.run())


if __name__ == '__main__':
    main()
