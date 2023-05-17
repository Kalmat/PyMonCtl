#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from typing import List, Tuple, TypedDict, Optional, NamedTuple


__all__ = [
    "enableUpdate", "disableUpdate", "isUpdateEnabled", "updateInterval",
    "getMonitors", "getMonitorsCount", "findMonitorName", "findMonitorInfo",
    "getSize", "getWorkArea", "getMousePos", "Structs",
    "getCurrentMode", "getAllowedModes", "changeMode",
]
# Mac only
__version__ = "0.0.3"


def version(numberOnly: bool = True):
    """Returns the current version of PyMonCtl module, in the form ''x.x.xx'' as string"""
    return ("" if numberOnly else "PyMonCtl-")+__version__


class Structs:

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

    BoundingBox = Rect  # BoundingBox is an alias for Rect class (just for retro-compatibility)

    class Point(NamedTuple):
        x: int
        y: int

    class Size(NamedTuple):
        width: int
        height: int

    class ScreenValue(TypedDict):
        id: int
        is_primary: bool
        pos: Structs.Point
        size: Structs.Size
        workarea: Structs.Rect
        scale: Tuple[int, int]
        dpi: Tuple[int, int]
        orientation: int
        frequency: float
        colordepth: int

    class DisplayMode(NamedTuple):
        width: int
        height: int
        frequency: float


def _pointInBox(x: int, y: int, left: int, top: int, width: int, height: int):
    """Returns ``True`` if the ``(x, y)`` point is within the box described
    by ``(left, top, width, height)``."""
    return left < x < left + width and top < y < top + height


class _UpdateScreens(threading.Thread):

    def __init__(self, interval: float = 0.3,
                 monitorCountChanged: Optional[Callable[[List[str], dict[str, Structs.ScreenValue]], None]] = None,
                 monitorPropsChanged: Optional[Callable[[List[str], dict[str, Structs.ScreenValue]], None]] = None):
        threading.Thread.__init__(self)

        self._kill = threading.Event()
        self._interval = interval
        self._monitorCountChanged = monitorCountChanged
        self._monitorPropsChanged = monitorPropsChanged
        self._screens: dict[str, Structs.ScreenValue] = getMonitors()
        self._count = _getMonitorsCount()

    def run(self):

        while not self._kill.is_set():

            screens = getMonitors(forceUpdate=True)
            currentScreens = list(self._screens.keys())

            if self._monitorCountChanged is not None:
                count = _getMonitorsCount()
                if self._count != count:
                    self._count = count
                    newScreens = list(screens.keys())
                    names = [s for s in newScreens if s not in currentScreens] + [s for s in currentScreens if s not in newScreens]
                    self._monitorCountChanged(names, screens)

            if self._monitorPropsChanged is not None:
                if self._screens != screens:
                    names = []
                    for s in screens.keys():
                        if s in currentScreens:
                            if screens[s] != self._screens[s]:
                                names.append(s)
                    self._monitorPropsChanged(names, screens)
            self._screens = screens

            self._kill.wait(self._interval)

    def updateInterval(self, interval: float):
        self._interval = interval

    def getScreens(self):
        return self._screens

    def kill(self):
        self._kill.set()


_updateScreens: Optional[_UpdateScreens] = None
_screens: dict[str, Structs.ScreenValue] = {}


def enableUpdate(interval: float = 0.3,
                 monitorCountChanged: Optional[Callable[[List[str], dict[str, Structs.ScreenValue]], None]] = None,
                 monitorPropsChanged: Optional[Callable[[List[str], dict[str, Structs.ScreenValue]], None]] = None):
    """
    Enable this only if you need to keep track of monitor-related events like changing its resolution, position,
    or if monitors can be dynamically plugged or unplugged in a multi-monitor setup. And specially if you rely on
    getDisplay() method to somehow control window objects.

    If enabled, it will activate a separate thread which will periodically update the list of monitors and
    their properties (see getMonitors() function).

    If disabled, the information on the monitors connected to the system will be static as it was when
    PyMonCtl module was initially loaded (changes produced afterwards will not be detected nor updated).

    It is also possible to define callbacks to be invoked in case the number of connected monitors or their
    properties change. The information passed to the callbacks is:

        - Names of the screens which have changed (as a list of strings)
        - All screens info, as returned by getMonitors() function.

    It is possible to access all their properties by using screen name as dictionary key

    :param interval: Wait interval for the thread loop in seconds (or fractions). Adapt to your needs. Defaults to 0.3.
                     Higher values will take longer to detect and notify changes.
                     Lower values will consume more CPU
    :param monitorCountChanged: callback to be invoked in case the number of monitor connected changes
    :param monitorPropsChanged: callback to be invoked in case the properties of connected monitors change

    """
    global _updateScreens
    if _updateScreens is None:
        _updateScreens = _UpdateScreens(interval, monitorCountChanged, monitorPropsChanged)
        _updateScreens.daemon = True
        _updateScreens.start()


def disableUpdate():
    """
    Stop and kill thread. The information of the monitors will remain static (not updated)
    after disabling this process.

    Enable this process again, or invoke getMonitors(forceUpdate=True) function if you need updated info.
    """
    global _updateScreens
    if _updateScreens is not None:
        _updateScreens.kill()
        _updateScreens.join()
        _updateScreens = None


def isUpdateEnabled() -> bool:
    """
    Get monitors watch process status (enabled / disabled)

    :return: Returns ''True'' if enabled.
    """
    global _updateScreens
    return bool(_updateScreens is not None)


def updateInterval(interval: float):
    """
    Change the wait interval for the thread loop in seconds (or fractions)
    Higher values will take longer to detect and notify changes.
    Lower values will consume more CPU

    :param interval: new interval value as float
    """
    global _updateScreens
    if interval > 0 and _updateScreens is not None:
        _updateScreens.updateInterval(interval)


def getMonitors(forceUpdate: bool = False) -> dict[str, Structs.ScreenValue]:
    """
    Get all monitors info plugged to the system, as a dict.

    If watchdog thread is enabled or the 'forceUpdate' param is set to ''True'', it will return updated information.
    Otherwise, it will return the monitors info as it was when the PyMonCtl module was initially loaded (static).

    Use 'forceUpdate' carefully since it can be CPU-consuming and slow in scenarios in which this function is
    repeatedly and quickly invoked, so if it is directly called or indirectly by other functions.

    :param forceUpdate: Set to ''True'' to force update the monitors information
    :return: Monitors info as python dictionary

    Output Format:
        Key:
            Display name

        Values:
            "id":
                display index as returned by EnumDisplayDevices()
            "is_primary":
                ''True'' if monitor is primary (shows clock and notification area, sign in, lock, CTRL+ALT+DELETE screens...)
            "pos":
                Point(x, y) struct containing the display position ((0, 0) for the primary screen)
            "size":
                Size(width, height) struct containing the display size, in pixels
            "workarea":
                Rect(left, top, right, bottom) struct with the screen workarea, in pixels
            "scale":
                Scale ratio, as a tuple of (x, y) scale percentage
            "dpi":
                Dots per inch, as a tuple of (x, y) dpi values
            "orientation":
                Display orientation: 0 - Landscape / 1 - Portrait / 2 - Landscape (reversed) / 3 - Portrait (reversed)
            "frequency":
                Refresh rate of the display, in Hz
            "colordepth":
                Bits per pixel referred to the display color depth
    """
    global _updateScreens
    global _screens
    if not _screens or forceUpdate:
        _screens = _getAllScreens()
    else:
        if _updateScreens is not None:
            _screens = _updateScreens.getScreens()
    return _screens


def getWorkArea(name: str = ""):
    """
    Get coordinates (left, top, right, bottom), in pixels, of the working (usable by windows) area
    of the given screen, or main screen if no screen name provided

    :param name: name of the monitor as returned by getMonitors() and getDisplay() methods.
    :return: Rect struct or None
    """
    return _getWorkArea(name)


def getSize(name: str = ""):
    """
    Get the width and height, in pixels, of the given monitor, or main monitor if no monitor name provided

    :param name: name of the monitor as returned by getMonitors() and getDisplay() methods.
    :return: Size struct or None
    """
    return _getScreenSize(name)


def getPosition(name: str = "") -> Optional[Structs.Point]:
    """
    Get position (x, y) of the given monitor, or main monitor if no monitor name provided

    :param name: name of the monitor as returned by getMonitors() and getDisplay() methods.
    :return: Point struct or None
    """
    return _getPosition(name)


def getRect(name: str = "") -> Optional[Structs.Rect]:
    """
    Get rect (x, y) of the given monitor, or main monitor if no monitor name provided

    :param name: name of the monitor as returned by getMonitors() and getDisplay() methods.
    :return: Point struct or None
    """
    return _getRect(name)


def findMonitorInfo(x: int, y: int) -> dict[str, Structs.ScreenValue]:
    """
    Get monitor info in which given coordinates are found.

    :return: monitor info (see getMonitors() doc) as dictionary, or empty
    """
    info: dict[str, Structs.ScreenValue] = {}

    screens = getMonitors()
    for monitor in screens.keys():
        pos = screens[monitor]["pos"]
        size = screens[monitor]["size"]
        if _pointInBox(x, y, pos.x, pos.y, size.width, size.height):
            info[monitor] = screens[monitor]
            break
    return info


def findMonitorName(x: int, y: int) -> str:
    """
    Get monitor name in which given coordinates are found.

    :return: monitor name or empty, as string
    """
    return _findMonitorName(x, y)


def getMonitorsCount() -> int:
    """
    Get the number of monitors currently connected to the system.

    :return: number of monitors as integer
    """
    return int(_getMonitorsCount())


def getMousePos():
    """
    Get the current (x, y) coordinates of the mouse pointer on screen, in pixels

    :return: Point struct
    """
    return _getMousePos()


def getCurrentMode(name: str = "") -> Optional[Structs.DisplayMode]:
    """
    Get the current monitor mode (width, height, refresh-rate) for the monitor identified by name (or primary if empty)

    :param name: name of the monitor as returned by getMonitors() method
    :return: current mode as DisplayMode struct
    """
    return _getCurrentMode(name)


def getAllowedModes(name: str = "") -> List[Structs.DisplayMode]:
    """
    Get all allowed modes for the monitor identified by name (or primary if empty)

    :param name: name of the monitor as returned by getMonitors() method
    :return: allowed modes as list of DisplayMode structs
    """
    return _getAllowedModes(name)


def changeMode(width: int, height: int, frequency: float, name: str = ""):
    """
    Change current monitor mode (resolution and/or refresh-rate) for the monitor identified by name (or primary if empty)

    The mode must be one of the allowed modes by the monitor (see getAllowedModes()).

    :param width: target width of screen
    :param height: target height of screen
    :param frequency: target refresh-rate of screen
    :param name: name of the monitor as returned by getMonitors() method
    """
    _changeMode(Structs.DisplayMode(width, height, frequency), name)


def _changeScale(scale: float, name: str = ""):
    _changeScale(scale, name)


def _changeOrientation(orientation: int, name: str = ""):
    _changeOrientation(orientation, name)


def _changePosition(newX: int, newY: int, name: str = ""):
    _changePosition(newX, newY, name)


if sys.platform == "darwin":
    from ._pymonctl_macos import (_getAllScreens, _getWorkArea, _getMonitorsCount, _getScreenSize, _getMousePos,
                                  _getCurrentMode, _getAllowedModes, _changeMode, _changeScale, _changeOrientation,
                                  _changePosition, _getPosition, _getRect, _findMonitorName
                                  )

elif sys.platform == "win32":
    from ._pymonctl_win import (_getAllScreens, _getWorkArea, _getMonitorsCount, _getScreenSize, _getMousePos,
                                _getCurrentMode, _getAllowedModes, _changeMode, _changeScale, _changeOrientation,
                                _changePosition, _getPosition, _getRect, _findMonitorName
                                )

elif sys.platform == "linux":
    from ._pymonctl_linux import (_getAllScreens, _getWorkArea, _getMonitorsCount, _getScreenSize, _getMousePos,
                                  _getCurrentMode, _getAllowedModes, _changeMode, _changeScale, _changeOrientation,
                                  _changePosition, _getPosition, _getRect, _findMonitorName
                                  )

else:
    raise NotImplementedError('PyMonCtl currently does not support this platform. If you think you can help, please contribute! https://github.com/Kalmat/PyMonCtl')

_screens = getMonitors(forceUpdate=True)
