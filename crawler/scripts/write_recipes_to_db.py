import aiokafka
import psycopg2
from psycopg2.extras import Json
from psycopg2.extensions import register_adapter

import asyncio
import typing
from crawler.queue_processors import QueueProcessor
from crawler import settings
import json
import statsd
import structlog

register_adapter(dict, Json)

logger = structlog.get_logger()

stats = statsd.StatsClient(
    host=settings.config["statsd"]["host"],
    port=int(settings.config["statsd"]["port"]),
    prefix=settings.config["statsd"]["prefix"]
)
db = psycopg2.connect(
    database=settings.config["postgres"]["database"],
    host=settings.config["postgres"]["host"],
    user=settings.config["postgres"]["user"],
    password=settings.config["postgres"]["password"],
    port=int(settings.config["postgres"]["port"]),
)
cursor = db.cursor()


class RecipeCollector(QueueProcessor):
    read_topic = 'recipes'
    group_id = 'persist_recipes_to_postgres'
    from_beginning = False

    INSERT_RECIPE_SQL = """
    INSERT INTO recipes (payload)
    VALUES (%s);
    """

    def __init__(self, from_beginning=False):
        super().__init__()
        self.from_beginning = from_beginning

    @stats.timer('decode_message')
    def decode_message(self, message: typing.Union[bytes, str]) -> typing.Dict[str, typing.Any]:
        if isinstance(message, bytes):
            message = message.decode('utf-8')
        return json.loads(message)

    @stats.timer('write_recipe_to_postgres')
    async def process_message(self, message: typing.Dict[str, typing.Any]):
        cursor.execute(self.INSERT_RECIPE_SQL, (message,))
        db.commit()

    async def setup_consumer(self):
        await super().setup_consumer()
        if not self.from_beginning:
            return
        logger.info("Seeking all the way to the first message of 'recipes'.")
        await self.consumer.seek_to_beginning(
            *[
                aiokafka.TopicPartition('recipes', partition)
                for partition in self.consumer.partitions_for_topic('recipes')
            ]
        )


def main():
    # Set from_beginning to True if we want to
    # read the entire topic from the beginning.
    db_writer = RecipeCollector(from_beginning=False)
    asyncio.get_event_loop().run_until_complete(db_writer.run())


if __name__ == '__main__':
    main()
