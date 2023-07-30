import urllib.parse

import msgpack
import pydantic
import typing


class Link(pydantic.BaseModel):
    url: str
    metadata: typing.Optional[typing.Dict[str, typing.Any]] = None

    _hostname: typing.Optional[str] = None

    @property
    def hostname(self) -> str:
        if self._hostname is None:
            self._hostname = urllib.parse.urlparse(self.url).hostname or 'unknown'
        return self._hostname


class CrawlResult(pydantic.BaseModel):
    url: str
    elapsed_time: typing.Optional[float] = None
    contents: typing.Optional[bytes] = None
    status_code: typing.Optional[int] = None
    timestamp: typing.Optional[str] = None
    _hostname: typing.Optional[str] = None

    @property
    def hostname(self) -> str:
        if self._hostname is None:
            self._hostname = urllib.parse.urlparse(self.url).hostname or 'unknown'
        return self._hostname

    @classmethod
    def from_msgpack(cls, value):
        return cls(**msgpack.unpackb(value))
