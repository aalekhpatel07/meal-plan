#!/usr/bin/env python

import datetime

import redis
from crawler import settings


cache = redis.StrictRedis(
    host=settings.config["redis"]["host"],
    port=settings.config["redis"]["port"]
)


if __name__ == '__main__':
    keys = cache.keys('chat_gpt3_parsed:*')
    pipe = cache.pipeline(transaction=True)
    for key in keys:
        pipe.expire(key.decode('utf-8'), datetime.timedelta(days=180))
    pipe.execute(raise_on_error=True)

