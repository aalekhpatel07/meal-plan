import typing
import abc
import aiokafka
import kafka.errors
import msgpack
import json
import structlog
import asyncio
import redis
from crawler import settings

logger = structlog.getLogger()

T = typing.TypeVar('T')

class QueueProcessor:

    read_topic: str
    group_id: typing.Optional[str] = None
    kafka_config: typing.Optional[typing.Dict[str, str]] = None
    redis_config: typing.Optional[typing.Dict[str, typing.Any]] = None
    cache: typing.Optional[redis.Redis] = None

    _consumer: typing.Optional[aiokafka.AIOKafkaConsumer] = None
    _producer: typing.Optional[aiokafka.AIOKafkaProducer] = None

    def __init__(self):
        self._producer_cache = dict()
        base_kafka_config = {**settings.config["kafka"]}
        if self.kafka_config:
            base_kafka_config.update(self.kafka_config)
        self.kafka_config = base_kafka_config
        self.redis_config = {**settings.config["redis"]}
        self.cache = redis.Redis(**self.redis_config)

    @property
    def consumer(self) -> aiokafka.AIOKafkaConsumer:
        if self._consumer is None:
            self._consumer = aiokafka.AIOKafkaConsumer(self.read_topic, group_id=self.group_id, **self.kafka_config)
            logger.info("Creating consumer...", read_topic=self.read_topic, group_id=self.group_id, kafka_config=self.kafka_config)
        return self._consumer

    @property
    def producer(self) -> aiokafka.AIOKafkaProducer:
        if self._producer is None:
            self._producer = aiokafka.AIOKafkaProducer(**self.kafka_config)
            logger.info(
                "Creating producer...",
                kafka_config=self.kafka_config
            )
        return self._producer

    def decode_message(self, message: typing.Union[bytes, str]) -> T:
        raise NotImplementedError("Should be implemented by subclasses.")

    async def process_message(self, message: T):
        raise NotImplementedError("Should be implemented by subclasses.")

    async def run(self):
        _ = self.consumer
        _ = self.producer
        try:
            await self.consumer.start()
        except kafka.errors.KafkaError as exc:
            logger.exception("kafka error", exception=exc)
            await self.consumer.stop()
            await self.producer.stop()
            return

        try:
            await self.producer.start()
        except kafka.errors.KafkaError as exc:
            logger.exception("kafka error", exception=exc)
            await self.producer.stop()
            # return

        try:
            async for msg in self.consumer:
                msg: aiokafka.ConsumerRecord = msg
                message_decoded = self.decode_message(msg.value)
                logger.debug("Message received:", message=msg)
                asyncio.ensure_future(self.process_message(message_decoded))
                logger.debug("waiting for next message")
        finally:
            logger.debug("awaiting consumer.stop()")
            await self.consumer.stop()
            await self.producer.stop()
