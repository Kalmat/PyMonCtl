#!/usr/bin/python
# -*- coding: utf-8 -*-
# Incomplete type stubs for pyobjc
# mypy: disable_error_code = no-any-return
from __future__ import annotations

import json
import sys

assert sys.platform == "darwin"

import subprocess
import threading
import time

from typing import Optional, List, Union, cast, Tuple

import AppKit
import Quartz
import Quartz.CoreGraphics as CG

from ._main import BaseMonitor, _pointInBox, _getRelativePosition, \
                   DisplayMode, ScreenValue, Box, Rect, Point, Size, Position, Orientation
from ._display_manager_lib import Display


def _getAllMonitors() -> list[MacOSMonitor]:
    monitors = []
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        monitors.append(MacOSMonitor(displayId))
    # Alternatives to test:
    v, ids, cnt = CG.CGGetOnlineDisplayList(10, None, None)
    v, ids, cnt = CG.CGGetActiveDisplayList(10, None, None)
    return monitors


def _getAllMonitorsDict(forceUpdate: bool = True) -> dict[str, ScreenValue]:
    result: dict[str, ScreenValue] = {}
    for mon in _NSgetAllMonitors():
        screen, desc, displayId, scrName = mon

        try:
            name = screen.localizedName()
        except:
            # In older macOS, screen doesn't have localizedName() method
            name = "Display" + "_" + str(displayId)
        display = displayId
        is_primary = Quartz.CGDisplayIsMain(display) == 1
        x, y, w, h = int(screen.frame().origin.x), int(screen.frame().origin.y), int(screen.frame().size.width), int(screen.frame().size.height)
        wa = screen.visibleFrame()
        wx, wy, wr, wb = int(wa.origin.x), int(wa.origin.y), int(wa.size.width), int(wa.size.height)
        scale = _getScale(screen)
        dpi = desc[Quartz.NSDeviceResolution].sizeValue()
        dpiX, dpiY = int(dpi.width), int(dpi.height)
        rot = int(Quartz.CGDisplayRotation(display))
        freq = Quartz.CGDisplayModeGetRefreshRate(Quartz.CGDisplayCopyDisplayMode(display))
        depth = Quartz.CGDisplayBitsPerPixel(display)

        result[scrName] = {
            'system_name': name,
            'id': displayId,
            'is_primary': is_primary,
            'position': Point(x, y),
            'size': Size(w, h),
            'workarea': Rect(wx, wy, wr, wb),
            'scale': scale,
            'dpi': (dpiX, dpiY),
            'orientation': rot,
            'frequency': freq,
            'colordepth': depth
        }
    return result


def _getMonitorsCount() -> int:
    return len(AppKit.NSScreen.screens())


def _findMonitor(x: int, y: int) -> List[MacOSMonitor]:
    ret, monIds, count = CG.CGGetDisplaysWithPoint((x, y), 10, None, None)
    monitors = []
    if ret == 0:
        for i in range(count):
            monitors.append(MacOSMonitor(monIds[i]))
    return monitors


def _getPrimary() -> MacOSMonitor:
    return MacOSMonitor()


def _arrangeMonitors(arrangement: dict[str, dict[str, Union[str, int, Position, Point, Size]]]):

    monitors = _NSgetAllMonitorsDict()
    for monName in monitors.keys():
        if monName not in arrangement.keys():
            return
    primaryPresent = False
    setAsPrimary = ""
    for monName in arrangement.keys():
        relPos = arrangement[monName]["relativePos"]
        relMon = arrangement[monName]["relativeTo"]
        if monName not in monitors.keys() or (relMon and relMon not in monitors.keys()) or \
                (not relMon and relPos != Position.PRIMARY):
            return
        elif relPos == Position.PRIMARY:
            setAsPrimary = monName
            primaryPresent = True
    if not primaryPresent:
        return

    newPos: dict[str, dict[str, int]] = {}
    newPos[setAsPrimary] = {"x": 0, "y": 0}
    commitChanges = True
    ret, configRef = Quartz.CGBeginDisplayConfiguration(None)
    if ret != 0:
        return

    x, y = 0, 0
    ret = Quartz.CGConfigureDisplayOrigin(configRef, monitors[setAsPrimary]["displayId"], x, y)
    if ret != 0:
        commitChanges = False

    for monName in arrangement.keys():
        if monName != setAsPrimary:

            relativePos = cast(Position, arrangement[monName]["relativePos"])
            relativeTo = str(arrangement[monName]["relativeTo"])

            frame = monitors[monName]["screen"].frame()
            targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                         "position": Point(frame.origin.x, frame.origin.y),
                         "size": Size(frame.size.width, frame.size.height)}

            frame = monitors[relativeTo]["screen"].frame()
            if relativeTo in newPos.keys():
                relX, relY = newPos[relativeTo]["x"], newPos[relativeTo]["y"]
            else:
                relX, relY = x, y
            relMon = {"position": Point(relX, relY), "size": Size(frame.size.width, frame.size.height)}

            x, y = _getRelativePosition(targetMon, relMon)
            ret = Quartz.CGConfigureDisplayOrigin(configRef, monitors[monName]["displayId"], x, y)
            newPos[monName] = {"x": x, "y": y}
            if ret != 0:
                commitChanges = False

    if commitChanges:
        Quartz.CGCompleteDisplayConfiguration(configRef, Quartz.kCGConfigurePermanently)
    else:
        Quartz.CGCancelDisplayConfiguration(configRef)


def _getMousePos(flipValues: bool = False) -> Point:
    """
    Get the current (x, y) coordinates of the mouse pointer on screen, in pixels

    Notice in AppKit the origin (0, 0) is bottom left (unflipped), which may differ to coordinates obtained
    using AppScript or CoreGraphics (flipped). To manage this, use 'flipValues' accordingly.

    :param flipValues: set to ''True'' to convert coordinates to origin (0, 0) at upper left corner
    :return: Point struct
    """
    # https://stackoverflow.com/questions/3698635/getting-cursor-position-in-python/24567802
    mp = Quartz.NSEvent.mouseLocation()
    x, y = int(mp.x), int(mp.y)
    if flipValues:
        screens = AppKit.NSScreen.screens()
        for screen in screens:
            frame = screen.frame()
            sx, sy, sw, sh = int(frame.origin.x), int(frame.origin.y), int(frame.size.width), int(frame.size.height)
            if _pointInBox(x, y, sx, sy, sw, sh):
                y = (-1 if y < 0 else 1) * (int(sh) - abs(y))
                break
    return Point(x, y)


class MacOSMonitor(BaseMonitor):

    def __init__(self, handle: Optional[int] = None):
        """
        Class to access all methods and functions to get info and manage monitors plugged to the system.

        This class is not meant to be directly instantiated. Instead, use convenience functions like getAllMonitors(),
        getPrimary() or findMonitor(x, y).

        It can raise ValueError exception in case provided handle is not valid
        """
        if not handle:
            self.screen = AppKit.NSScreen.mainScreen()
            self.handle = Quartz.CGMainDisplayID()
        else:
            self.screen = None
            self.handle = handle
            for screen in AppKit.NSScreen.screens():
                desc = screen.deviceDescription()
                displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
                if handle == displayId:
                    self.screen = screen
                    break
        if self.screen is not None:
            self.name = _getName(self.handle, self.screen)
            self._dm = Display(self.handle)
        else:
            raise ValueError

    @property
    def size(self, ) -> Optional[Size]:
        size = self.screen.frame().size
        res = Size(int(size.width), int(size.height))
        return res

    @property
    def workarea(self) -> Optional[Rect]:
        wa = self.screen.visibleFrame()
        wx, wy, wr, wb = int(wa.origin.x), int(wa.origin.y), int(wa.size.width), int(wa.size.height)
        res = Rect(wx, wy, wr, wb)
        return res

    @property
    def position(self) -> Optional[Point]:
        origin = self.screen.frame().origin
        res = Point(int(origin.x), int(origin.y))
        return res

    def setPosition(self, relativePos: Union[int, Position], relativeTo: Optional[str]):
        _setPosition(cast(Position, relativePos), relativeTo, self.name)

    @property
    def box(self) -> Optional[Box]:
        frame = self.screen.frame()
        res = Box(int(frame.origin.x), int(frame.origin.y), int(frame.size.width), int(frame.size.height))
        return res

    @property
    def rect(self) -> Optional[Rect]:
        frame = self.screen.frame()
        res = Rect(int(frame.origin.x), int(frame.origin.y),
                   int(frame.origin.x) + int(frame.size.width), int(frame.origin.y) + int(frame.size.height))
        return res

    @property
    def scale(self) -> Optional[Tuple[float, float]]:
        scale = _getScale(self.screen)
        # mode = Quartz.CGDisplayCopyDisplayMode(self.handle)
        # w = Quartz.CGDisplayModeGetWidth(mode)
        # pw = Quartz.CGDisplayModeGetPixelWidth(mode)
        # h = Quartz.CGDisplayModeGetHeight(mode)
        # ph = Quartz.CGDisplayModeGetPixelHeight(mode)
        # f = Quartz.CGDisplayModeGetRefreshRate(mode)
        # scale2 = ((pw / w) * 100, (ph / h) * 100)
        return scale

    def setScale(self, scale: Tuple[float, float]):
        # https://www.eizoglobal.com/support/compatibility/dpi_scaling_settings_mac_os_x/
        # if scale is not None:
        #     scaleX, scaleY = scale
        #     currWidth, currHeight = self.size
        #     currScaleX, currScaleY = self.scale
        #     targetWidth = currScaleX / scaleX * currWidth
        #     targetHeight = currScaleY / scaleY * currHeight
        #     for mode in _CGgetAllModes(self.handle):
        #         w = Quartz.CGDisplayModeGetWidth(mode)
        #         pw = Quartz.CGDisplayModeGetPixelWidth(mode)
        #         h = Quartz.CGDisplayModeGetHeight(mode)
        #         ph = Quartz.CGDisplayModeGetPixelHeight(mode)
        #         f = Quartz.CGDisplayModeGetRefreshRate(mode)
        #         if targetWidth == pw or targetHeight == ph:
        #             CG.CGDisplaySetDisplayMode(self.handle, mode, None)
        #             break
        pass

    @property
    def dpi(self) -> Optional[Tuple[float, float]]:
        desc = self.screen.deviceDescription()
        dpi = desc[Quartz.NSDeviceResolution].sizeValue()
        dpiX, dpiY = int(dpi.width), int(dpi.height)
        return dpiX, dpiY

    @property
    def orientation(self) -> Optional[Union[int, Orientation]]:
        orientation = int(Quartz.CGDisplayRotation(self.handle) / 90)
        if orientation in (Orientation.NORMAL, Orientation.INVERTED, Orientation.LEFT, Orientation.RIGHT):
            return orientation
        return None

    def setOrientation(self, orientation: Optional[Union[int, Orientation]]):
        if orientation in (Orientation.NORMAL, Orientation.INVERTED, Orientation.LEFT, Orientation.RIGHT):
            self._dm.setRotate(orientation * 90)

    @property
    def frequency(self) -> Optional[float]:
        freq = Quartz.CGDisplayModeGetRefreshRate(Quartz.CGDisplayCopyDisplayMode(self.handle))
        return freq

    @property
    def colordepth(self) -> Optional[int]:
        depth = Quartz.CGDisplayBitsPerPixel(self.handle)
        return depth

    @property
    def brightness(self) -> Optional[int]:
        return self._dm.brightness
        # https://stackoverflow.com/questions/46885603/is-there-a-programmatic-way-to-check-if-brightness-is-at-max-or-min-value-on-osx
        # value = None
        # cmd = """nvram backlight-level | awk '{print $2}'"""
        # err, ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "")
        # if err == 0 and ret:
        #     value = int(float(ret)) * 100
        # return value

    def setBrightness(self, brightness: Optional[int]):
        try:
            self._dm.setBrightness(brightness)
        except:
            pass
        # https://github.com/thevickypedia/pybrightness/blob/main/pybrightness/controller.py
        # https://eastmanreference.com/complete-list-of-applescript-key-codes
        # for _ in range(32):
        #     os.system("""osascript -e 'tell application "System Events"' -e 'key code 145' -e ' end tell'""")
        # for _ in range(round((32 * int(brightness)) / 100)):
        #     os.system("""osascript -e 'tell application "System Events"' -e 'key code 144' -e ' end tell'""")

    @property
    def contrast(self) -> Optional[int]:
        # https://searchcode.com/file/2207916/pyobjc-framework-Quartz/PyObjCTest/test_cgdirectdisplay.py/
        contrast = None
        try:
            ret, redMin, redMax, redGamma, greenMin, greenMax, greenGamma, blueMin, blueMax, blueGamma = (
                CG.CGGetDisplayTransferByFormula(self.handle, None, None, None, None, None, None, None, None, None))
            if ret == 0:
                contrast = int(((1 / (float(redGamma) or 1)) + (1 / (float(greenGamma) or 1)) + (1 / (float(blueGamma) or 1))) / 3) * 100
        except:
            pass
        return contrast

    def setContrast(self, contrast: Optional[int]):
        # https://searchcode.com/file/2207916/pyobjc-framework-Quartz/PyObjCTest/test_cgdirectdisplay.py/
        if contrast is not None:
            try:
                ret, redMin, redMax, redGamma, greenMin, greenMax, greenGamma, blueMin, blueMax, blueGamma = (
                    CG.CGGetDisplayTransferByFormula(self.handle, None, None, None, None, None, None, None, None, None))
                if ret == 0:
                    newRedGamma = contrast / 100
                    if newRedGamma < redMin:
                        newRedGamma = redMin
                    elif newRedGamma > redMax:
                        newRedGamma = redMax
                    newGreenGamma = contrast / 100
                    if newGreenGamma < greenMin:
                        newGreenGamma = greenMin
                    elif newGreenGamma > greenMax:
                        newGreenGamma = greenMax
                    newBlueGamma = contrast / 100
                    if newBlueGamma < blueMin:
                        newBlueGamma = blueMin
                    elif newBlueGamma > blueMax:
                        newBlueGamma = blueMax
                    ret = CG.CGSetDisplayTransferByFormula(self.handle,
                                                           redMin, redMax, newRedGamma,
                                                           greenMin, greenMax, newGreenGamma,
                                                           blueMin, blueMax, newBlueGamma
                                                           )
            except:
                pass

    @property
    def mode(self) -> Optional[DisplayMode]:
        mode = Quartz.CGDisplayCopyDisplayMode(self.handle)
        w = Quartz.CGDisplayModeGetWidth(mode)
        h = Quartz.CGDisplayModeGetHeight(mode)
        r = Quartz.CGDisplayModeGetRefreshRate(mode)
        return DisplayMode(w, h, r)

    def setMode(self, mode: Optional[DisplayMode]):
        # https://stackoverflow.com/questions/10596489/programmatically-change-resolution-os-x
        # https://searchcode.com/file/2207916/pyobjc-framework-Quartz/PyObjCTest/test_cgdirectdisplay.py/
        if mode is not None:
            allModes = _CGgetAllModes(self.handle)
            for m in allModes:
                if (mode.width == Quartz.CGDisplayModeGetWidth(m) and
                        mode.height == Quartz.CGDisplayModeGetHeight(m) and
                        mode.frequency == Quartz.CGDisplayModeGetRefreshRate(m)):
                    CG.CGDisplaySetDisplayMode(self.handle, m, None)
                    break
            # Look for best mode to apply or stick to input?
            #         return
            # bestMode, ret = CG.CGDisplayBestModeForParametersAndRefreshRate(self.handle, self.colordepth,
            #                                                                 mode.width, mode.height, mode.frequency,
            #                                                                 None)
            # CG.CGDisplaySwitchToMode(self.handle, bestMode)


    @property
    def defaultMode(self) -> Optional[DisplayMode]:
        res: Optional[DisplayMode] = None
        modes = _CGgetAllModes(self.handle)
        for mode in modes:
            if bin(Quartz.CGDisplayModeGetIOFlags(mode))[-3] == '1':
                w = Quartz.CGDisplayModeGetWidth(mode)
                h = Quartz.CGDisplayModeGetHeight(mode)
                r = Quartz.CGDisplayModeGetRefreshRate(mode)
                res = DisplayMode(w, h, r)
                break
        return res

    def setDefaultMode(self):
        modes = _CGgetAllModes(self.handle)
        for mode in modes:
            if bin(Quartz.CGDisplayModeGetIOFlags(mode))[-3] == '1':
                CG.CGDisplaySetDisplayMode(self.handle, mode, None)
                break

    @property
    def allModes(self) -> List[DisplayMode]:
        modes: List[DisplayMode] = []
        for mode in _CGgetAllModes(self.handle):
            w = Quartz.CGDisplayModeGetWidth(mode)
            h = Quartz.CGDisplayModeGetHeight(mode)
            r = Quartz.CGDisplayModeGetRefreshRate(mode)
            modes.append(DisplayMode(w, h, r))
        modesSet = set(modes)
        return list(modesSet)

    @property
    def isPrimary(self):
        return self.handle == Quartz.CGMainDisplayID()

    def setPrimary(self):
        # https://stackoverflow.com/questions/13722508/change-main-monitor-on-mac-programmatically#:~:text=To%20change%20the%20secondary%20monitor%20to%20be%20the,%28%29.%20A%20full%20sample%20can%20be%20found%20Here
        self.setPosition(Position.PRIMARY, "")

    def turnOn(self):
        # This works, but won't wake up the display despite if the mouse is moving and/or clicking

        def mouseEvent(eventType, posx, posy):
            ev = CG.CGEventCreateMouseEvent(None, eventType, CG.CGPointMake(posx, posy), CG.kCGMouseButtonLeft)
            CG.CGEventSetType(ev, eventType)
            # or kCGSessionEventTap?
            CG.CGEventPost(CG.kCGHIDEventTap, ev)
            # CG.CFRelease(ev)   # Produces a Hardware error?!?!?!

        def mousemove(posx, posy):
            # Alternatives:
            # mouseEvent(CG.kCGEventMouseMoved, posx, posy)
            CG.CGDisplayMoveCursorToPoint(self.handle, (posx, posy))

        def mouseclick(posx, posy):
            # Not necessary to previously move the mouse to given location
            # mouseEvent(CG.kCGEventMouseMoved, posx, posy)
            mouseEvent(CG.kCGEventLeftMouseDown, posx, posy)
            time.sleep(0.1)
            mouseEvent(CG.kCGEventLeftMouseUp, posx, posy)

        if CG.CGDisplayIsAsleep(self.handle):
            mousemove(200, 200)
            mouseclick(200, 200)
            # This won't wake up monitor either (refers to the whole system)
            # cmd = """pmset wake"""
            # subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)

        elif not CG.CGDisplayIsActive(self.handle):
            # CG.CGDisplayRelease(self.handle)
            pass

    def turnOff(self):
        # https://stackoverflow.com/questions/32319778/check-if-display-is-sleeping-in-applescript
        # CG.CGDisplayCapture(self.handle)  # This turns display black, not off
        pass

    @property
    def isOn(self) -> Optional[bool]:
        return bool(CG.CGDisplayIsActive(self.handle) == 1)

    def suspend(self):
        # Also injecting: Control–Shift–Media Eject
        cmd = """pmset displaysleepnow"""
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
        except:
            pass

    @property
    def isSuspended(self) -> Optional[bool]:
        return bool(CG.CGDisplayIsAsleep(self.handle) == 1)

    def attach(self, width: int = 0, height: int = 0):
        pass

    def detach(self, permanent: bool = False):
        # Maybe manipulating position, size and/or mode?
        pass

    @property
    def isAttached(self) -> Optional[bool]:
        return CG.CGDisplayIsOnline(self.handle) == 1


def _setPosition(relativePos: Union[int, Position], relativeTo: Optional[str], name: str):
    # https://apple.stackexchange.com/questions/249447/change-display-arrangement-in-os-x-macos-programmatically
    monitors = _NSgetAllMonitorsDict()
    if (name in monitors.keys() and
            (relativePos == Position.PRIMARY or (relativePos != Position.PRIMARY and relativeTo in monitors.keys()))):

        if relativePos == Position.PRIMARY:

            # If this display becomes primary (0, 0). MUST reposition primary monitor first!
            commitChanges = True
            ret, configRef = Quartz.CGBeginDisplayConfiguration(None)
            if ret != 0:
                return
            relativePos = Position.LEFT_TOP
            relativeTo = name
            newPos: dict[str, dict[str, int]] = {}
            for monitor in monitors.keys():
                if monitor != name:
                    frame = monitors[name]["screen"].frame()
                    targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                                 "position": Point(frame.origin.x, frame.origin.y),
                                 "size": Size(frame.size.width, frame.size.height)}

                    frame = monitors[relativeTo]["screen"].frame()
                    if relativeTo in newPos.keys():
                        relX, relY = newPos[relativeTo]["x"], newPos[relativeTo]["y"]
                    else:
                        relX, relY = frame.origin.x, frame.origin.y
                    relMon = {"position": Point(relX, relY),
                              "size": Size(frame.size.width, frame.size.height)}

                    x, y = _getRelativePosition(targetMon, relMon)
                    ret = Quartz.CGConfigureDisplayOrigin(configRef, monitors[monitor]["displayId"], x, y)
                    newPos[monitor] = {"x": x, "y": y}
                    if ret != 0:
                        commitChanges = False
                    relativeTo = monitor

            x, y = 0, 0
            ret = Quartz.CGConfigureDisplayOrigin(configRef, monitors[name]["displayId"], x, y)
            if ret != 0:
                commitChanges = False

            if commitChanges:
                Quartz.CGCompleteDisplayConfiguration(configRef, Quartz.kCGConfigurePermanently)
            else:
                Quartz.CGCancelDisplayConfiguration(configRef)

        else:

            frame = monitors[name]["screen"].frame()
            targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                         "position": Point(frame.origin.x, frame.origin.y),
                         "size": Size(frame.size.width, frame.size.height)}

            frame = monitors[relativeTo]["screen"].frame()
            relMon = {"position": Point(frame.origin.x, frame.origin.y),
                      "size": Size(frame.size.width, frame.size.height)}

            x, y = _getRelativePosition(targetMon, relMon)
            ret, configRef = Quartz.CGBeginDisplayConfiguration(None)
            if ret == 0:
                ret = Quartz.CGConfigureDisplayOrigin(configRef, monitors[name]["displayId"], x, y)
                if ret == 0:
                    Quartz.CGCompleteDisplayConfiguration(configRef, Quartz.kCGConfigurePermanently)
                else:
                    Quartz.CGCancelDisplayConfiguration(configRef)


def _getName(displayId: int, screen: Optional[AppKit.NSScreen] = None):
    if not screen:
        screen = AppKit.NSScreen.mainScreen()
    try:
        if screen is not None:
            scrName = screen.localizedName() + "_" + str(displayId)
    except:
        # In older macOS, screen doesn't have localizedName() method
        scrName = "Display" + "_" + str(displayId)
    return scrName


def _getScale(screen):
    value = float(screen.backingScaleFactor() * 100)
    scale = (value, value)
    return scale


def _CGgetAllModes(handle, showHiDpi: bool = True):
    # Test this with all combinations:
    flags = {}
    if showHiDpi:
        flags[Quartz.kCGDisplayShowDuplicateLowResolutionModes] = Quartz.kCFBooleanTrue
    return Quartz.CGDisplayCopyAllDisplayModes(handle, flags)


def _NSgetAllMonitors():
    monitors = []
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        scrName = _getName(displayId, screen)
        monitors.append([screen, desc, displayId, scrName])
    return monitors


def _NSgetAllMonitorsDict():
    monitors = {}
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        scrName = _getName(displayId, screen)
        monitors[scrName] = {"screen": screen, "desc": desc, "displayId": displayId}
    return monitors


def _eventLoop(kill: threading.Event, interval: float):

    def reconfig(displayId, flags, userInfo):
        '''
        FLAGS:
        beginConfigurationFlag:
            The display configuration is about to change.
        movedFlag:
            The location of the upper-left corner of the display in the global display coordinate space has changed.
        setMainFlag:
            The display is now the main display.
        setModeFlag:
            The display mode has changed.
        addFlag:
            The display has been added to the active display list.
        removeFlag:
            The display has been removed from the active display list.
        enabledFlag:
            The display has been enabled.
        disabledFlag:
            The display has been disabled.
        mirrorFlag:
            The display is now mirroring another display.
        unMirrorFlag:
            The display is no longer mirroring another display.
        desktopShapeChangedFlag
        '''
        print("RECONFIG", displayId, flags, userInfo)

    Quartz.CGDisplayRegisterReconfigurationCallback(reconfig, None)
    while not kill.is_set():
        kill.wait(interval)
    Quartz.CGDisplayRemoveReconfigurationCallback(reconfig, None)
