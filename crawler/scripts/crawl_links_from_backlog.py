#!/usr/bin/env python

import asyncio
import datetime
import typing

import httpx
import math
import bs4
import urllib.parse
import json
import recipe_scrapers

import structlog
import msgpack
import statsd

from crawler.models import (
    CrawlResult,
    Link
)
from crawler import settings
from crawler.queue_processors import QueueProcessor

logger = structlog.getLogger()

CRAWL_RECENCY_PERIOD = 60 * 60 * 24 * 7


stats = statsd.StatsClient(
    prefix=settings.config["statsd"]["prefix"]
)


class Crawler(QueueProcessor):
    read_topic = "links"
    client: typing.Optional[httpx.AsyncClient] = None
    group_id = "crawler"

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(
            follow_redirects=True,
            timeout=30
        )

    @stats.timer('crawl')
    async def crawl(self, link: Link) -> typing.Optional[CrawlResult]:
        headers = {}
        if link.metadata:
            referrer = link.metadata.get("referrer", None)
            if referrer:
                headers["referrer"] = referrer

        start_time = datetime.datetime.now()
        response = await self.client.get(link.url, headers=headers)
        end_time = datetime.datetime.now()
        elapsed = end_time - start_time
        logger.debug(
            "performed crawl:",
            elapsed=f"{elapsed.total_seconds():.8f}",
            status=response.status_code,
            url=link.url,
            metadata=link.metadata,
        )
        crawl_duration_rounded = math.ceil(elapsed.total_seconds())
        stats.incr(
            f'links_crawled,'
            f'hostname={link.hostname},'
            f'status={response.status_code},'
            f'time_taken_less_than={crawl_duration_rounded}'
        )

        stats.incr(f'scraped_bytes,hostname={link.hostname}', count=len(response.content))

        if not response.is_success:
            logger.error("Crawl failed", url=link.url, status=response.status_code)
            stats.incr(f'failed_crawls,status={response.status_code},hostname={link.hostname}')
            return

        result = CrawlResult(
            url=link.url,
            elapsed_time=elapsed.total_seconds(),
            contents=response.content,
            status_code=response.status_code,
            timestamp=end_time.isoformat()
        )
        return result

    @stats.timer('has_link_been_visited_recently')
    def has_link_been_visited_recently(self, url: str) -> bool:
        if self.cache.get(f"visited__{url}"):
            return True
        self.cache.set(f"visited__{url}", 1, ex=CRAWL_RECENCY_PERIOD)
        return False

    def is_url_nofollow(self, url: str, crawl_result: CrawlResult):  # noqa
        return url == crawl_result.url

    @stats.timer('get_links')
    def get_links(self, crawl_result: CrawlResult) -> typing.Generator[Link, None, None]:
        soup = bs4.BeautifulSoup(crawl_result.contents.decode('utf-8'))
        for anchor in soup.find_all("a"):
            url = anchor.get('href', None)
            if not url:
                continue
            url = urllib.parse.urljoin(crawl_result.url, url)
            hostname = urllib.parse.urlparse(url).hostname
            if self.is_url_nofollow(url, crawl_result):
                continue
            if self.has_link_been_visited_recently(url):
                stats.incr(f'duplicate_url,hostname={hostname}')
                continue
            yield Link(url=url, metadata={'referrer': crawl_result.url})

    @stats.timer('decode_message')
    def decode_message(self, message: typing.Union[bytes, str]) -> Link:
        if isinstance(message, bytes):
            message = message.decode('utf-8')
        return Link(**json.loads(message))

    @stats.timer('scrape_recipe_from_crawl_result')
    async def try_scraping_recipe_from_crawl_result(self, crawl_result: CrawlResult) -> bool:
        try:
            contents = crawl_result.contents.decode('utf-8')
        except UnicodeError:
            logger.error(f"Crawl for {crawl_result.url} yielded non-utf8 contents.")
            stats.incr(f'utf8_invalid_contents,hostname={crawl_result.hostname}')
            return False
        try:
            logger.debug("Trying to scrape recipe:", url=crawl_result.url)
            scraped = recipe_scrapers.scrape_html(contents)
            stats.incr(f'recipe_scrapes,success=True,hostname={crawl_result.hostname}')
        except recipe_scrapers.NoSchemaFoundInWildMode as exc:
            logger.warn(
                f"Failed to scrape URL.",
                url=exc.url,
                message=exc.message
            )
            stats.incr(f'recipe_scrapes,success=False,hostname={crawl_result.hostname}')
            return False
        else:
            scraped_contents = json.dumps(scraped.to_json())
            logger.debug(
                "Found recipe:",
                author=scraped.author(),
                url=scraped.url
            )
            await self.producer.send('recipes', scraped_contents.encode('utf-8'))
            return True

    async def process_message(self, link: Link):
        logger.debug("Processing message:", link=link)
        crawl_result = await self.crawl(link)
        could_scrape_recipe = await self.try_scraping_recipe_from_crawl_result(crawl_result)
        if could_scrape_recipe:
            links_found = 0
            for link in self.get_links(crawl_result):
                links_found += 1
                await self.producer.send('links', link.model_dump_json().encode('utf-8'))
            stats.incr(f'outbound_links_discovered,hostname={crawl_result.hostname}', count=links_found)


def main():
    crawler = Crawler()
    asyncio.get_event_loop().run_until_complete(crawler.run())


if __name__ == '__main__':
    main()
