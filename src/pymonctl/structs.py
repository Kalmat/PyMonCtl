#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

from enum import IntEnum
from typing import NamedTuple, TypedDict, Tuple


class Box(NamedTuple):
    left: int
    top: int
    width: int
    height: int


class Rect(NamedTuple):
    left: int
    top: int
    right: int
    bottom: int


class Point(NamedTuple):
    x: int
    y: int


class Size(NamedTuple):
    width: int
    height: int


class ScreenValue(TypedDict):
    system_name: str
    handle: int
    is_primary: bool
    position: Point
    size: Size
    workarea: Rect
    scale: Tuple[int, int]
    dpi: Tuple[int, int]
    orientation: int
    frequency: float
    colordepth: int


class DisplayMode(NamedTuple):
    width: int
    height: int
    frequency: float


class Position(IntEnum):
    PRIMARY = 0
    LEFT_TOP = 10
    LEFT_BOTTOM = 15
    ABOVE_LEFT = 20
    ABOVE_RIGHT = 25
    RIGHT_TOP = 30
    RIGHT_BOTTOM = 35
    BELOW_LEFT = 40
    BELOW_RIGHT = 45


class Orientation(IntEnum):
    ROTATE_0 = 0
    NORMAL = 0
    ROTATE_90 = 1
    RIGHT = 1
    ROTATE_180 = 2
    INVERTED = 2
    ROTATE_270 = 3
    LEFT = 3


# Position values to be directly used
PRIMARY = 0
LEFT_TOP = 10
LEFT_BOTTOM = 15
ABOVE_LEFT = 20
ABOVE_RIGHT = 25
RIGHT_TOP = 30
RIGHT_BOTTOM = 35
BELOW_LEFT = 40
BELOW_RIGHT = 45


# Orientation values to be directly used
ROTATE_0 = 0
NORMAL = 0
ROTATE_90 = 1
RIGHT = 1
ROTATE_180 = 2
INVERTED = 2
ROTATE_270 = 3
LEFT = 3
