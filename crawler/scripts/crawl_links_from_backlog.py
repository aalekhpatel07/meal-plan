#!/usr/bin/env python

import asyncio
import datetime
import typing

import httpx
import json

import structlog
import msgpack

from crawler.models import (
    CrawlResult,
    Link
)
from crawler.queue_processors import QueueProcessor

logger = structlog.getLogger()


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
            status=response.status_code,
            url=link.url,
            metadata=link.metadata,
            response_headers=response.headers
        )

        if not response.is_success:
            logger.error("Crawl failed", url=link.url, status=response.status_code)
            return

        result = CrawlResult(
            url=link.url,
            elapsed_time=elapsed.total_seconds(),
            contents=response.content,
            status_code=response.status_code,
            timestamp=end_time.isoformat()
        )
        await self.producer.send('crawl-results', msgpack.packb(result.model_dump()))
        logger.debug("Sent to crawl-results")

        return result

    def decode_message(self, message: typing.Union[bytes, str]) -> Link:
        if isinstance(message, bytes):
            message = message.decode('utf-8')
        return Link(**json.loads(message))

    async def process_message(self, link: Link):
        logger.info("Processing message...")
        logger.info("Seen link", link=link)
        crawl_result = await self.crawl(link)
        if crawl_result:
            logger.debug(
                "Crawl finished",
                elapsed_time=crawl_result.elapsed_time,
                url=crawl_result.url,
                content_length=len(crawl_result.contents),
                status_code=crawl_result.status_code
            )


def main():
    crawler = Crawler()
    asyncio.get_event_loop().run_until_complete(crawler.run())


if __name__ == '__main__':
    main()
