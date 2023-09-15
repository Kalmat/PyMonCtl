#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import threading
from abc import abstractmethod, ABC
from collections.abc import Callable
from typing import List, Optional, Union, Tuple

from ._structs import DisplayMode, ScreenValue, Size, Point, Box, Rect, Position, Orientation


def _pointInBox(x: int, y: int, left: int, top: int, width: int, height: int) -> bool:
    """Returns ``True`` if the ``(x, y)`` point is within the box described
    by ``(left, top, width, height)``."""
    return left <= x <= left + width and top <= y <= top + height


def getAllMonitors() -> list[Monitor]:
    """
    Get the list with all Monitor instances from plugged monitors.

    In case you plan to use this function in a scenario in which it could be invoked quickly and repeatedly,
    it's highly recommended to enable update watchdog (see enableUpdate() function).

    :return: list of Monitor instances
    """
    global _updateScreens
    if _updateScreens is None:
        return _getAllMonitors()
    else:
        return _updateScreens.getMonitors()


def getAllMonitorsDict() -> dict[str, ScreenValue]:
    """
    Get all monitors info plugged to the system, as a dict.

    In case you plan to use this function in a scenario in which it could be invoked quickly and repeatedly,
    it's highly recommended to enable update watchdog (see enableUpdate() function).

    :return: Monitors info as python dictionary

    Output Format:
        Key:
            Display name (in macOS it is necessary to add handle to avoid duplicates)

        Values:
            "system_name":
                display name as returned by the system (in macOS, the name can be duplicated!)
            "handle":
                display handle according to each platform/OS
            "is_primary":
                ''True'' if monitor is primary (shows clock and notification area, sign in, lock, CTRL+ALT+DELETE screens...)
            "position":
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
    if _updateScreens is None:
        return _getAllMonitorsDict()
    else:
        return _updateScreens.getScreens()


def getMonitorsCount() -> int:
    """
    Get the number of monitors currently connected to the system.

    :return: number of monitors as integer
    """
    return _getMonitorsCount()


def getPrimary() -> Monitor:
    """
    Get primary monitor instance. This is equivalent to invoking ''Monitor()'', with empty input params.

    :return: Monitor instance or None
    """
    return _getPrimary()


def findMonitor(x: int, y: int) -> List[Monitor]:
    """
    Get monitor instance in which given coordinates (x, y) are found.

    :return: Monitor instance or None
    """
    return _findMonitor(x, y)


def findMonitorInfo(x: int, y: int) -> dict[str, ScreenValue]:
    """
    Get monitor info in which given coordinates (x, y) are found.

    :return: monitor info (see getAllMonitorsDict() doc) as dictionary, or empty
    """
    info: dict[str, ScreenValue] = {}
    monitors = getAllMonitorsDict()
    for monitor in monitors.keys():
        pos = monitors[monitor]["position"]
        size = monitors[monitor]["size"]
        if _pointInBox(x, y, pos.x, pos.y, size.width, size.height):
            info[monitor] = monitors[monitor]
    return info


def arrangeMonitors(arrangement: dict[str, dict[str, Union[str, int, Position, Point, Size]]]):
    """
    Arrange all monitors in a given shape.

    For that, you must pass a dict with the following structure:
        "Monitor name":
            monitor name as keys() returned by getAllMonitorsDict() (don't use "system_name" value for this)
                "relativePos":
                    position of this monitor in relation to the monitor provided in ''relativeTo''
                "relativeTo":
                    monitor name to which ''relativePos'' is referred to (or None if PRIMARY)


    You MUST pass the position of ALL monitors, and SET ONE of them as PRIMARY.

    HIGHLY RECOMMENDED: When building complex arrangements, start by the primary monitor and then build the rest
    taking previous ones as references.

    EXAMPLE for a 3-Monitors setup in which second is at the left and third is on top of primary monitor:

        {
            "Display_1": {"relativePos": Position.PRIMARY, "relativeTo": None},

            "Display_2": {"relativePos": Position.LEFT_TOP, "relativeTo": "Display_1"},

            "Display_3": {"relativePos": Position.ABOVE_LEFT, "relativeTo": "Display_1"}
        }

    :param arrangement: arrangement structure as dict
    """
    _arrangeMonitors(arrangement)


def getMousePos() -> Point:
    """
    Get the current (x, y) coordinates of the mouse pointer on screen, in pixels

    :return: Point struct
    """
    return _getMousePos()


class BaseMonitor(ABC):

    @property
    @abstractmethod
    def size(self) -> Optional[Size]:
        """
        Get the dimensions of the monitor as a size struct (width, height)

        This property can not be set independently. To do so, choose an allowed mode (from monitor.allModes)
        and set the monitor mode property (monitor.mode = selectedMode)

        :return: Size
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def workarea(self) -> Optional[Rect]:
        """
        Get dimensions of the "usable by applications" area (screen size minus docks, taskbars and so on), as
        a rect struct (x, y, right, bottom)

        This property can not be set.

        :return: Rect
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def position(self) -> Optional[Point]:
        """
        Get monitor position coordinates as a point struct (x, y)

        This property can not be set. Use setPosition() method instead.

        :return: Point
        """
        raise NotImplementedError

    @abstractmethod
    def setPosition(self, relativePos: Union[int, Position, Point, Tuple[int, int]], relativeTo: Optional[str]):
        """
        Change relative position of the current the monitor in relation to another existing monitor (e.g. primary monitor).

        On Windows and macOS, setting position to (0, 0) will also mean setting the monitor as primary, and viceversa;
        but not on Linux (on Linux, combine setPrimary() and setPosition() to get desired config).

        In general, it is HIGHLY recommendable to use arrangeMonitors() method instead of setPosition(), and most
        especially in complex arrangements or setups with more than 2 monitors.

        Important OS-dependent behaviors and limitations:

        - On Windows, primary monitor is mandatory, and it is always placed at (0, 0) coordinates. Besides, the monitors can not overlap. To set a monitor as Primary, it is necessary to reposition primary monitor first, so the rest of monitors will sequentially be repositioned to LEFT.

        - On Linux, primary monitor can be anywhere, and even there can be no primary monitor. Monitors can overlap, so take this into account when setting a new monitor position. Also bear in mind that xranr won't accept negative values, so the whole config will be referenced to (0, 0) coordinates.

        - On macOS, primary monitor is mandatory, and it is always placed at (0, 0) coordinates. The monitors can overlap. To set a monitor as Primary, it is necessary to reposition primary monitor first, so the rest of monitors will sequentially be repositioned to LEFT.

        :param relativePos: position in relation to another existing monitor (e.g. primary) as per Positions.*
        :param relativeTo: monitor in relation to which this monitor must be placed
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def box(self) -> Optional[Box]:
        """
        Get monitor dimensions as a box struct (x, y, width, height)

        This property can not be set.

        :return: Box
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def rect(self) -> Optional[Rect]:
        """
        Get monitor dimensions as a rect struct (x, y, right, bottom)

        This property can not be set.

        :return: Rect
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def scale(self) -> Optional[Tuple[float, float]]:
        """
        Get scale for the monitor

        Note not all scales will be allowed for all monitors and/or modes
        """
        raise NotImplementedError

    @abstractmethod
    def setScale(self, scale: Tuple[float, float]):
        """
        Change scale for the monitor

        Note not all scales will be allowed for all monitors and/or modes

        :param scale: target percentage as float value
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def dpi(self) -> Optional[Tuple[float, float]]:
        """
        Get the dpi (dots/pixels per inch) value for the monitor

        This property can not be set
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def orientation(self) -> Optional[Union[int, Orientation]]:
        """
        Get current orientation for the monitor identified by name (or primary if empty)

        The available orientations are:
            0 - 0 degrees (normal)
            1 - 90 degrees (right)
            2 - 180 degrees (inverted)
            3 - 270 degrees (left)
        """
        raise NotImplementedError

    @abstractmethod
    def setOrientation(self, orientation: Optional[Union[int, Orientation]]):
        """
        Change orientation for the monitor identified by name (or primary if empty)

        The available orientations are:
            0 - 0 degrees (normal)
            1 - 90 degrees (right)
            2 - 180 degrees (inverted)
            3 - 270 degrees (left)

        :param orientation: orientation as per Orientations.*
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def frequency(self) -> Optional[float]:
        """
        Get current refresh rate of monitor.

        This property can not be set independently. To do so, choose an allowed mode (from monitor.allModes)
        and set the monitor mode property (monitor.mode = selectedMode)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def colordepth(self) -> Optional[int]:
        """
        Get the colordepth (bits per pixel to describe color) value for the monitor

        This property can not be set
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def brightness(self) -> Optional[int]:
        """
        Get the brightness of monitor. The return value is normalized to 0-100 (as a percentage)

        :return: brightness as float
        """
        raise NotImplementedError

    @abstractmethod
    def setBrightness(self, brightness: Optional[int]):
        """
        Change the brightness of monitor. The input parameter must be defined as a percentage (0-100)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def contrast(self) -> Optional[int]:
        """
        Get the contrast of monitor. The return value is normalized to 0-100 (as a percentage)

        WARNING: In Linux and macOS contrast is calculated from Gamma RGB values.

        :return: contrast as float
        """
        raise NotImplementedError

    @abstractmethod
    def setContrast(self, contrast: Optional[int]):
        """
        Change the contrast of monitor. The input parameter must be defined as a percentage (0-100)

        WARNING: In Linux and macOS the change will apply to Gamma homogeneously for all color components (R, G, B).

        Example for Linux: A value of 50.0 (50%), will result in a Gamma of ''0.5:0.5:0.5''
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def mode(self) -> Optional[DisplayMode]:
        """
        Get the current monitor mode (width, height, refresh-rate) for the monitor

        :return: current mode as DisplayMode struct
        """
        raise NotImplementedError

    @abstractmethod
    def setMode(self, mode: Optional[DisplayMode]):
        """
        Change current monitor mode (resolution and/or refresh-rate) for the monitor

        The mode must be one of the allowed modes by the monitor (see allModes property).

        :param mode: target mode as DisplayMode (width, height and frequency)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def defaultMode(self) -> Optional[DisplayMode]:
        """
        Get the preferred mode for the monitor

        :return: DisplayMode struct (width, height, frequency)
        """
        raise NotImplementedError

    @abstractmethod
    def setDefaultMode(self):
        """
        Change current mode to default / preferred mode
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def allModes(self) -> list[DisplayMode]:
        """
        Get all allowed modes for the monitor

        :return: list of DisplayMode (width, height, frequency)
        """
        raise NotImplementedError

    @property
    def isPrimary(self) -> bool:
        """
        Check if given monitor is primary.

        :return: ''True'' if given monitor is primary, ''False'' otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def setPrimary(self):
        """
        Set monitor as the primary one.

        WARNING: Notice this can also change the monitor position, altering the whole monitors setup.
        To properly handle this, use arrangeMonitors() instead.
        """
        raise NotImplementedError

    @abstractmethod
    def turnOn(self):
        """
        Turn on or wakeup monitor if it was off or suspended (but not if it is detached).
        """
        raise NotImplementedError

    @abstractmethod
    def turnOff(self):
        """
        Turn off monitor

        WARNING:

            Windows:
                If monitor has no VCP MCCS support, it can not be addressed separately, so ALL monitors will be turned off.
                To address a specific monitor, try using detach() method

            macOS:
                Didn't find a way to programmatically turn off a given monitor. Use suspend instead.
        """
        raise NotImplementedError

    @abstractmethod
    def suspend(self):
        """
        Suspend (standby) monitor

        WARNING:

            Windows:
                If monitor has no VCP MCCS support, it can not be addressed separately, so ALL monitors will be suspended.
                To address a specific monitor, try using detach() method

            Linux:
                This method will suspend ALL monitors.

            macOS:
                This method will suspend ALL monitors.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def isOn(self) -> Optional[bool]:
        """
        Check if monitor is on

        WARNING: not working in macOS (... yet?)
        """
        raise NotImplementedError

    @abstractmethod
    def attach(self):
        """
        Attach a previously detached monitor to system

        All monitor IDs will change after detaching or attaching a monitor. The module will try to refresh them for
        all existing instances

        WARNING: not working in macOS (... yet?)
        """
        raise NotImplementedError

    @abstractmethod
    def detach(self, permanent: bool = False):
        """
        Detach monitor from system.

        Be aware that if you detach a monitor and the script ends, you will have to physically re-attach the monitor.

        All monitor IDs will change after detaching or attaching a monitor. The module will try to refresh them for
        all existing instances

        It will not likely work if system has just one monitor plugged.

        WARNING: not working in macOS (... yet?)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def isAttached(self) -> Optional[bool]:
        """
        Check if monitor is attached (not necessarily ON) to system
        """
        raise NotImplementedError


_updateRequested = False
_plugListeners: List[Callable[[List[str], dict[str, ScreenValue]], None]] = []
_lockPlug = threading.RLock()
_changeListeners: List[Callable[[List[str], dict[str, ScreenValue]], None]] = []
_lockChange = threading.RLock()
_kill = threading.Event()


class _UpdateScreens(threading.Thread):

    def __init__(self, kill: threading.Event):
        threading.Thread.__init__(self)

        self._kill = kill
        self._interval = 0.5
        self._screens: dict[str, ScreenValue] = _getAllMonitorsDict()
        self._monitors: list[Monitor] = []

    def run(self):

        # _eventLoop(self._kill, self._interval)

        global _updateRequested
        global _plugListeners
        global _changeListeners

        while not self._kill.is_set():

            if _updateRequested or _plugListeners or _changeListeners:

                screens = _getAllMonitorsDict()
                newScreens = list(screens.keys())
                currentScreens = list(self._screens.keys())

                if currentScreens != newScreens:
                    names = [s for s in newScreens if s not in currentScreens] + \
                            [s for s in currentScreens if s not in newScreens]
                    for listener in _plugListeners:
                        listener(names, screens)

                if self._screens != screens:
                    names = [s for s in newScreens if s in currentScreens and screens[s] != self._screens[s]]
                    self._screens = screens
                    if names:
                        for listener in _changeListeners:
                            listener(names, screens)

                self._monitors = _getAllMonitors()

            self._kill.wait(self._interval)

    def updateInterval(self, interval: float):
        self._interval = interval

    def getScreens(self) -> dict[str, ScreenValue]:
        return self._screens

    def getMonitors(self) -> list[Monitor]:
        return self._monitors


_updateScreens: Optional[_UpdateScreens] = None
_lockUpdate = threading.RLock()


def enableUpdateInfo():
    """
    Enable this only if you need to keep track of monitor-related events like changing its resolution, position,
    or if monitors can be dynamically plugged or unplugged in a multi-monitor setup. This function can also be
    useful in scenarios in which monitors list or properties need to be queried quickly and repeatedly, thus keeping
    this information updated without impacting main process.

    If enabled, it will activate a separate thread which will periodically update the list of monitors and
    their properties (see getAllMonitors() and getAllMonitorsDict() functions).

    If disabled, the information on the monitors connected to the system will be updated right at the moment,
    but this might be slow and CPU-consuming, especially if quickly and repeatedly invoked.
    """
    global _updateRequested
    _updateRequested = True
    if _updateScreens is None:
        _startUpdateScreens()


def disableUpdateInfo():
    """
    The monitors information will be immediately queried after disabling this feature, not taking advantage of
    keeping information updated on a separate thread.

    Enable this process again, or invoke getMonitors() function if you need updated info.
    """
    global _updateRequested
    _updateRequested = False
    if not _plugListeners and not _changeListeners and not _updateRequested:
        _killUpdateScreens()


def plugListenerRegister(monitorCountChanged: Callable[[List[str], dict[str, ScreenValue]], None]):
    """
    Use this only if you need to keep track of monitor that can be dynamically plugged or unplugged in a
    multi-monitor setup.

    The registered callbacks will be invoked in case the number of connected monitors change.
    The information passed to the callbacks is:

        - Names of the screens which have changed (as a list of strings).
        - All screens info, as returned by getAllMonitorsDict() function.

    It is possible to access all monitors information by using screen name as dictionary key

    :param monitorCountChanged: callback to be invoked in case the number of monitor connected changes
    """
    global _plugListeners
    global _lockPlug
    with _lockPlug:
        if monitorCountChanged not in _plugListeners:
            _plugListeners.append(monitorCountChanged)
    if _updateScreens is None:
        _startUpdateScreens()


def plugListenerUnregister(monitorCountChanged: Callable[[List[str], dict[str, ScreenValue]], None]):
    """
    Use this function to un-register your custom callback. The callback will not be invoked anymore in case
    the number of monitor changes.

    :param monitorCountChanged: callback previously registered
    """
    global _plugListeners
    global _lockPlug
    with _lockPlug:
        try:
            objIndex = _plugListeners.index(monitorCountChanged)
            _plugListeners.pop(objIndex)
        except:
            pass
    if not _plugListeners and not _changeListeners and not _updateRequested:
        _killUpdateScreens()


def changeListenerRegister(monitorPropsChanged: Callable[[List[str], dict[str, ScreenValue]], None]):
    """
    Use this only if you need to keep track of monitor properties changes (position, size, refresh-rate, etc.) in a
    multi-monitor setup.

    The registered callbacks will be invoked in case these properties change.
    The information passed to the callbacks is:

        - Names of the screens which have changed (as a list of strings).
        - All screens info, as returned by getAllMonitorsDict() function.

    It is possible to access all monitor information by using screen name as dictionary key

    :param monitorPropsChanged: callback to be invoked in case the number of monitor properties change
    """
    global _changeListeners
    global _lockChange
    with _lockChange:
        if monitorPropsChanged not in _changeListeners:
            _changeListeners.append(monitorPropsChanged)
    if _updateScreens is None:
        _startUpdateScreens()


def changeListenerUnregister(monitorPropsChanged: Callable[[List[str], dict[str, ScreenValue]], None]):
    """
    Use this function to un-register your custom callback. The callback will not be invoked anymore in case
    the monitor properties change.

    :param monitorPropsChanged: callback previously registered
    """
    global _changeListeners
    global _lockChange
    with _lockChange:
        try:
            objIndex = _plugListeners.index(monitorPropsChanged)
            _plugListeners.pop(objIndex)
        except:
            pass
    if not _plugListeners and not _changeListeners and not _updateRequested:
        _killUpdateScreens()


def _startUpdateScreens():
    global _updateScreens
    global _lockUpdate
    with _lockUpdate:
        if _updateScreens is None:
            _kill.clear()
            _updateScreens = _UpdateScreens(_kill)
            _updateScreens.daemon = True
            _updateScreens.start()


def _killUpdateScreens():
    global _updateScreens
    global _lockUpdate
    global _kill
    with _lockUpdate:
        if _updateScreens is not None:
            timer = threading.Timer(_updateScreens._interval * 2, _timerHandler)
            timer.start()
            try:
                _kill.set()
                _updateScreens.join(_updateScreens._interval * 3)
            except:
                pass
            _updateScreens = None
            timer.cancel()


class _TimeOutException(Exception):
    pass


def _timerHandler():
    global _updateScreens
    raise _TimeOutException()


def isWatchdogEnabled() -> bool:
    """
    Check if the daemon updating screens information and (if applies) invoking callbacks when needed is alive.

    If it is not, just enable update process, or register the callbacks you need. It will be automatically started.

    :return: Return ''True'' is process (thread) is alive
    """
    global _updateScreens
    return bool(_updateScreens is not None)


def isUpdateInfoEnabled() -> bool:
    """
    Get monitors watch process status (enabled / disabled).

    :return: Returns ''True'' if enabled.
    """
    global _updateRequested
    return _updateRequested


def isPlugListenerRegistered(monitorCountChanged: Callable[[List[str], dict[str, ScreenValue]], None]):
    """
    Check if callback is already registered to be invoked when monitor plugged count change

    :return: Returns ''True'' if registered
    """
    global _plugListeners
    return monitorCountChanged in _plugListeners


def isChangeListenerRegistered(monitorPropsChanged: Callable[[List[str], dict[str, ScreenValue]], None]):
    """
    Check if callback is already registered to be invoked when monitor properties change

    :return: Returns ''True'' if registered
    """
    global _changeListeners
    return monitorPropsChanged in _changeListeners


def updateWatchdogInterval(interval: float):
    """
    Change the wait interval for the thread loop in seconds (or fractions), Default is 0.50 seconds.

    Higher values will take longer to detect and notify changes.

    Lower values will make it faster, but will consume more CPU.

    Also bear in mind that the OS will take some time to refresh changes, so lowering the update interval
    may not necessarily produce better (faster) results.

    :param interval: new interval value in seconds (or fractions), as float.
    """
    global _updateScreens
    if interval > 0 and _updateScreens is not None:
        _updateScreens.updateInterval(interval)


def _getRelativePosition(monitor, relativeTo) -> Tuple[int, int]:
    relPos = monitor["relativePos"]
    if relPos == Position.PRIMARY:
        x = y = 0
    elif relPos == Position.LEFT_TOP:
        x = relativeTo["position"].x - monitor["size"].width
        y = relativeTo["position"].y
    elif relPos == Position.LEFT_BOTTOM:
        x = relativeTo["position"].x - monitor["size"].width
        y = relativeTo["position"].y + relativeTo["size"].height - monitor["size"].height
    elif relPos == Position.LEFT_CENTERED:
        x = relativeTo["position"].x - monitor["size"].width
        y = relativeTo["position"].y + ((relativeTo["size"].height - monitor["size"].height) // 2)
    elif relPos == Position.ABOVE_LEFT:
        x = relativeTo["position"].x
        y = relativeTo["position"].y - monitor["size"].height
    elif relPos == Position.ABOVE_RIGHT:
        x = relativeTo["position"].x + relativeTo["size"].width - monitor["size"].width
        y = relativeTo["position"].y - monitor["size"].height
    elif relPos == Position.ABOVE_CENTERED:
        x = relativeTo["position"].x + ((relativeTo["size"].width - monitor["size"].width) // 2)
        y = relativeTo["position"].y - monitor["size"].height
    elif relPos == Position.RIGHT_TOP:
        x = relativeTo["position"].x + relativeTo["size"].width
        y = relativeTo["position"].y
    elif relPos == Position.RIGHT_BOTTOM:
        x = relativeTo["position"].x + relativeTo["size"].width
        y = relativeTo["position"].y + relativeTo["size"].height - monitor["size"].height
    elif relPos == Position.RIGHT_CENTERED:
        x = relativeTo["position"].x + relativeTo["size"].width
        y = relativeTo["position"].y + ((relativeTo["size"].height - monitor["size"].height) // 2)
    elif relPos == Position.BELOW_LEFT:
        x = relativeTo["position"].x
        y = relativeTo["position"].y + relativeTo["size"].height
    elif relPos == Position.BELOW_RIGHT:
        x = relativeTo["position"].x + relativeTo["size"].width - monitor["size"].width
        y = relativeTo["position"].y + relativeTo["size"].height
    elif relPos == Position.BELOW_CENTERED:
        x = relativeTo["position"].x + ((relativeTo["size"].width - monitor["size"].width) // 2)
        y = relativeTo["position"].y + relativeTo["size"].height
    else:
        x = y = monitor["position"]
    return x, y


if sys.platform == "darwin":
    from ._pymonctl_macos import (_getAllMonitors, _getAllMonitorsDict, _getMonitorsCount, _getPrimary,
                                  _findMonitor, _arrangeMonitors, _getMousePos, MacOSMonitor as Monitor
                                  )
elif sys.platform == "win32":
    from ._pymonctl_win import (_getAllMonitors, _getAllMonitorsDict, _getMonitorsCount, _getPrimary,
                                _findMonitor, _arrangeMonitors, _getMousePos, Win32Monitor as Monitor
                                )
elif sys.platform == "linux":
    from ._pymonctl_linux import (_getAllMonitors, _getAllMonitorsDict, _getMonitorsCount, _getPrimary,
                                  _findMonitor, _arrangeMonitors, _getMousePos, LinuxMonitor as Monitor
                                  )
else:
    raise NotImplementedError('PyMonCtl currently does not support this platform. If you think you can help, please contribute! https://github.com/Kalmat/PyMonCtl')
