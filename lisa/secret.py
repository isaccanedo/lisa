# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import re
from typing import Any, List, Optional, Pattern, Set, Tuple, Union

PATTERN_GUID = (
    re.compile(r"^([0-9a-f]{8})-(?:[0-9a-f]{4}-){3}[0-9a-f]{8}([0-9a-f]{4})$"),
    r"\1-****-****-****-********\2",
)
PATTERN_HEADTAIL = (
    re.compile(r"^([\w])[\W\w]+([\w])$"),
    r"\1****\2",
)
PATTERN_FILENAME = (
    re.compile(r"^[^.]*?[\\/]?(.)[^\\/]*?(.[.]?[^.]*)$"),
    r"\1***\2",
)
# https://xx.core.windows.net/vhds/CentOS.vhd?sp=r&st=xx%2012:10:45&5;CA%aEMpls3D
# replace as https://xx.core.windows.net/vhds/CentOS.vhd***
PATTERN_URL = (
    re.compile(r"(https?://([-\w]+\.)+[-\w]+(/[-./\w]*)?\??)([\w]+=[%&-:;=\w]*)?$"),
    r"\1***",
)

patterns = {"guid": PATTERN_GUID, "headtail": PATTERN_HEADTAIL, "url": PATTERN_URL}


def replace(
    origin: Any,
    mask: Optional[Union[Pattern[str], Tuple[Pattern[str], str]]] = None,
    sub: str = "******",
) -> str:
    if mask:
        if isinstance(mask, tuple):
            configured_sub = mask[1]
            mask = mask[0]
        else:
            configured_sub = sub
        result = mask.sub(configured_sub, origin)
        if result == origin:
            # failed and fallback
            result = sub
        return result
    else:
        return sub


_secret_list: List[Tuple[str, str]] = []
_secret_set: Set[str] = set()


def reset() -> None:
    _secret_set.clear()
    _secret_list.clear()


def add_secret(
    origin: Any,
    mask: Optional[Union[Pattern[str], Tuple[Pattern[str], str]]] = None,
    sub: str = "******",
) -> None:
    global _secret_list
    if origin:
        if not isinstance(origin, str):
            origin = str(origin)
        if origin in _secret_set:
            for index, secret in enumerate(_secret_list):
                if origin == secret[0]:
                    _secret_list[index] = (origin, replace(origin, sub=sub, mask=mask))
                    break
        else:
            _secret_set.add(origin)
            _secret_list.append((origin, replace(origin, sub=sub, mask=mask)))
            # deal with longer first, in case it's broken by shorter
            _secret_list = sorted(_secret_list, reverse=True, key=lambda x: len(x[0]))


def mask(text: str) -> str:
    for secret in _secret_list:
        if secret[0] in text:
            text = text.replace(secret[0], secret[1])
    return text
