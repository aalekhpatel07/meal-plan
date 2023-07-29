import msgpack
import pydantic
import typing


class Link(pydantic.BaseModel):
    url: str
    metadata: typing.Optional[typing.Dict[str, typing.Any]] = None


class CrawlResult(pydantic.BaseModel):
    url: str
    elapsed_time: typing.Optional[float] = None
    contents: typing.Optional[bytes] = None
    status_code: typing.Optional[int] = None

    @classmethod
    def from_msgpack(cls, value):
        return cls(**msgpack.unpackb(value))
