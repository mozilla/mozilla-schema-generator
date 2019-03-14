# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from typing import Any, Tuple

from itertools import chain


def _get(_dict: dict, key: Tuple[str]) -> Any:
    """
    Retrieved the nested `key` from a dict
    """
    if key:
        return _get(_dict[key[0]], key[1:])
    return _dict


def prepend_properties(key: Tuple[str]) -> Tuple[str]:
    """
    Add a "properties" before each element of `key`.
    This allows the field to be retrieved in a JSON schema

    ex:
    ```
    >> key = ("hello", "world")
    >> _prepend_propertes(key)
    ("properties", "hello", "properties", "world)
    ```
    """
    return tuple(chain.from_iterable(zip(("properties" for k in key), key)))
