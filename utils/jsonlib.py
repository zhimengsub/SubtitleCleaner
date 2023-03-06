from datetime import datetime
from json import JSONEncoder as _JSONEncoder
from typing import Any

import ujson
from orjson import (
    JSONDecodeError as _JSONDecodeError,
    JSONEncodeError as _JSONEncodeError,
    dumps as json_dumps,
    loads as json_loads,
)

JSONEncodeError = _JSONEncodeError
JSONDecodeError = _JSONDecodeError


def _default(value: Any):
    if isinstance(value, datetime):
        return value.timestamp()
    return value


def loads(*args, **kwargs) -> Any:
    return json_loads(*args, **kwargs)


def load(*args, **kwargs) -> Any:
    return ujson.load(*args, **kwargs)


def dumps(*args, **kwargs) -> str:
    return json_dumps(*args, default=_default, **kwargs).decode(
        encoding="utf-8"
    )


def dump(*args, **kwargs) -> None:
    return ujson.dump(*args, **kwargs)


class JSONEncoder(_JSONEncoder):
    ...
