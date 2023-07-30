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
    kafka_producer_config: typing.Optional[typing.Dict[str, str]] = None
    kafka_consumer_config: typing.Optional[typing.Dict[str, str]] = None
    redis_config: typing.Optional[typing.Dict[str, typing.Any]] = None
    cache: typing.Optional[redis.Redis] = None

    _consumer: typing.Optional[aiokafka.AIOKafkaConsumer] = None
    _producer: typing.Optional[aiokafka.AIOKafkaProducer] = None

    def __init__(self):
        self._producer_cache = dict()
        base_consumer_config = {}
        base_producer_config = {}
        base_kafka_config = {**settings.config["kafka"]}
        if "kafka-consumer" in settings.config:
            base_consumer_config = {**settings.config["kafka-consumer"]}
        if "kafka-producer" in settings.config:
            base_producer_config = {**settings.config["kafka-producer"]}

        int_overrides = {"max_request_size"}

        for key in int_overrides:
            if key in base_consumer_config:
                base_consumer_config[key] = int(base_consumer_config[key])
            if key in base_producer_config:
                base_producer_config[key] = int(base_producer_config[key])

        self.kafka_consumer_config = base_consumer_config
        self.kafka_producer_config = base_producer_config
        if self.kafka_config:
            base_kafka_config.update(self.kafka_config)
        self.kafka_config = base_kafka_config
        self.redis_config = {**settings.config["redis"]}
        self.cache = redis.Redis(**self.redis_config)

    @property
    def consumer(self) -> aiokafka.AIOKafkaConsumer:
        if self._consumer is None:
            config_merged = {**self.kafka_config}
            if self.kafka_consumer_config:
                config_merged.update(self.kafka_consumer_config)
            self._consumer = aiokafka.AIOKafkaConsumer(
                self.read_topic,
                group_id=self.group_id,
                **config_merged
            )
            logger.info(
                "Creating consumer...",
                read_topic=self.read_topic,
                group_id=self.group_id,
                config=config_merged
            )
        return self._consumer

    @property
    def producer(self) -> aiokafka.AIOKafkaProducer:
        if self._producer is None:
            config_merged = {**self.kafka_config}
            if self.kafka_producer_config:
                config_merged.update(self.kafka_producer_config)
            self._producer = aiokafka.AIOKafkaProducer(**config_merged)
            logger.info(
                "Creating producer...",
                config=config_merged
            )
        return self._producer

    def decode_message(self, message: typing.Any) -> T:
        raise NotImplementedError("Should be implemented by subclasses.")

    async def process_message(self, message: T):
        raise NotImplementedError("Should be implemented by subclasses.")

    async def setup_consumer(self):
        _ = self.consumer
        try:
            await self.consumer.start()
        except kafka.errors.KafkaError as exc:
            logger.exception("kafka error", exception=exc)
            await self.consumer.stop()

    async def setup_producer(self):
        _ = self.producer
        try:
            await self.producer.start()
        except kafka.errors.KafkaError as exc:
            logger.exception("kafka error", exception=exc)
            await self.producer.stop()

    async def run(self):
        await self.setup_consumer()
        await self.setup_producer()
        try:
            logger.debug("Listening for messages...")
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
