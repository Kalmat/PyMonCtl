#!/usr/bin/python
# -*- coding: utf-8 -*-
# Incomplete type stubs for pyobjc
# mypy: disable_error_code = no-any-return
from __future__ import annotations

import subprocess
import sys
import threading
import time

assert sys.platform == "darwin"

from typing import Optional, List, Union

import AppKit
import Quartz
import Quartz.CoreGraphics as CG

from pymonctl import BaseMonitor, _pointInBox, _getRelativePosition
from .structs import *
# from display_manager import display_manager_lib as dm


def _getAllMonitors():
    monitors = []
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        monitors.append(Monitor(displayId))
    return monitors


def _getScale(screen):

    displayId = _NSgetDisplayId(screen.localizedName())
    scale = (0, 0)
    if displayId:
        mode = Quartz.CGDisplayCopyDisplayMode(displayId)
        # Didn't find a better way to find out if mode is hidpi or not
        highResModes = Quartz.CGDisplayCopyAllDisplayModes(displayId,
                                        {Quartz.kCGDisplayShowDuplicateLowResolutionModes: Quartz.kCFBooleanTrue})
        if mode in highResModes:
            pxWidth = Quartz.CGDisplayModeGetPixelWidth(mode)
            pxHeight = Quartz.CGDisplayModeGetPixelHeight(mode)
            resWidth = Quartz.CGDisplayModeGetWidth(mode)
            resHeight = Quartz.CGDisplayModeGetHeight(mode)
            scale = (pxWidth / resWidth, pxHeight / resHeight)
        else:
            value = int(screen.backingScaleFactor() * 100)
            scale = (value, value)
    return scale


def _getModeScale(mode):
    # Didn't find a better way to find out if mode is hidpi or not
    pxWidth = Quartz.CGDisplayModeGetPixelWidth(mode)
    pxHeight = Quartz.CGDisplayModeGetPixelHeight(mode)
    resWidth = Quartz.CGDisplayModeGetWidth(mode)
    resHeight = Quartz.CGDisplayModeGetHeight(mode)
    scale = (pxWidth / resWidth, pxHeight / resHeight)
    return scale


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
            'handle': displayId,
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


def _findMonitor(x: int, y: int) -> Optional[Monitor]:
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        frame = screen.frame()
        if _pointInBox(x, y, int(frame.origin.x), int(frame.origin.y), int(frame.size.width), int(frame.size.height)):
            desc = screen.deviceDescription()
            displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
            return Monitor(displayId)
    return None


def _getPrimary() -> Monitor:
    return Monitor()


def _arrangeMonitors(arrangement: dict[str, dict[str, Union[str, int, Position, Point, Size]]]):

    monitors = _NSgetAllMonitorsDict()

    targetArrangement: dict[str, dict[str, Union[str, int, Point, Size]]] = {}
    while len(arrangement) > len(targetArrangement):
        for monName in arrangement:
            relMon = arrangement[monName]["relativeTo"]
            relPos = arrangement[monName]["relativePos"]
            if monName not in monitors.keys() or (relMon and relMon not in monitors.keys()) or \
                    (not relMon and relPos != PRIMARY):
                return
            if monName not in targetArrangement.keys() and \
                    (relMon in targetArrangement.keys() or relPos == PRIMARY):
                frame = monitors[monName]["screen"].frame()
                arrangement[monName]["pos"] = Point(frame.origin.x, frame.origin.y)
                arrangement[monName]["size"] = Point(frame.size.width, frame.size.height)
                targetArrangement[monName] = arrangement[monName]
                x, y, _ = _getRelativePosition(arrangement[monName], targetArrangement[relMon] if relMon else None)
                targetArrangement[monName]["pos"] = Point(x, y)
                break

    for monName in targetArrangement:
        x, y = targetArrangement[monName]["pos"]
        _setPosition(x, y, monName)


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


class Monitor(BaseMonitor):

    def __init__(self, handle: Optional[int] = None):
        """
        Class to access all methods and functions to get info and manage monitors plugged to the system.

        This class is not meant to be directly instantiated. Instead, use convenience functions like getAllMonitors(),
        getPrimary() or findMonitor(x, y).
        """
        if not handle:
            self.screen = AppKit.NSScreen.mainScreen()
            self.handle = Quartz.CGMainDisplayID()
        else:
            self.handle = handle
            for screen in AppKit.NSScreen.screens():
                desc = screen.deviceDescription()
                displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
                if handle == displayId:
                    self.screen = screen
                    break
        try:
            self.name = self.screen.localizedName()
        except:
            # In older macOS, screen doesn't have localizedName() method
            self.name = "Display" + "_" + str(self.handle)

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

    def setPosition(self, relativePos: Union[int, Position], relativeTo: str):
        _setPosition(relativePos, relativeTo, self.name)

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
    def scale(self):
        return _getScale(self.screen)

    @scale.setter
    def scale(self, scale: float):
        # https://www.eizoglobal.com/support/compatibility/dpi_scaling_settings_mac_os_x/
        # Where is scale stored or how to calculate?
        # <CGDisplayMode 0x7fe8f44b2260> [{
        #     BitsPerPixel = 32;
        #     BitsPerSample = 8;
        #     DepthFormat = 4;
        #     Height = 1080;
        #     IODisplayModeID = 100;
        #     IOFlags = 15;
        #     Mode = 0;
        #     PixelEncoding = "--------RRRRRRRRGGGGGGGGBBBBBBBB";
        #     RefreshRate = 0;
        #     SamplesPerPixel = 3;
        #     UsableForDesktopGUI = 1;
        #     Width = 1920;
        #     kCGDisplayBytesPerRow = 7680;
        #     kCGDisplayHorizontalResolution = 72;
        #     kCGDisplayModeIsInterlaced = 0;
        #     kCGDisplayModeIsSafeForHardware = 1;
        #     kCGDisplayModeIsStretched = 0;
        #     kCGDisplayModeIsTelevisionOutput = 0;
        #     kCGDisplayModeIsUnavailable = 0;
        #     kCGDisplayModeSuitableForUI = 1;
        #     kCGDisplayPixelsHigh = 1080;
        #     kCGDisplayPixelsWide = 1920;
        #     kCGDisplayResolution = 1;
        #     kCGDisplayVerticalResolution = 72;
        # }]
        # displayId = __getDisplayId(name)
        # if displayId:
        #     screens = AppKit.NSScreen.screens()
        #     for screen in screens:
        #         desc = screen.deviceDescription()
        #         if desc["NSScreenNumber"] == displayId:
        #             allModes = _getAllowedModes(name)
        #             for mode in allModes:
        #                 # or kCGDisplayHorizontalResolution, kCGDisplayVerticalResolution?
        #                 if len(mode) >= 1 and mode[0]["kCGDisplayResolution"] == (scale / 100):
        #                     Quartz.CGDisplaySetDisplayMode(displayId, mode, None)
        #                     return
        mode = Quartz.CGDisplayCopyDisplayMode(self.handle)
        for m in Quartz.CGDisplayCopyAllDisplayModes(self.handle, {
                    Quartz.kCGDisplayShowDuplicateHighResolutionModes: Quartz.kCFBooleanTrue}):
            if Quartz.CGDisplayModeGetWidth(mode) == Quartz.CGDisplayModeGetWidth(m) and \
                    Quartz.CGDisplayModeGetHeight(mode) == Quartz.CGDisplayModeGetHeight(m) and \
                    _getModeScale(m) == (scale, scale):
                self.mode = m
                break

    @property
    def dpi(self):
        desc = self.screen.deviceDescription()
        dpi = desc[Quartz.NSDeviceResolution].sizeValue()
        dpiX, dpiY = int(dpi.width), int(dpi.height)
        return dpiX, dpiY

    @property
    def orientation(self) -> Optional[Union[int, Orientation]]:
        orientation = int(Quartz.CGDisplayRotation(self.handle) / 90)
        if orientation in (NORMAL, INVERTED, LEFT, RIGHT):
            return orientation
        return None

    @orientation.setter
    def orientation(self, orientation: Union[int, Orientation]):
        # display = dm.Display(self.handle)
        # if orientation in (NORMAL, INVERTED, LEFT, RIGHT):
        #     display.setRotate(orientation * 90)
        pass

    @property
    def frequency(self) -> float:
        freq = Quartz.CGDisplayModeGetRefreshRate(Quartz.CGDisplayCopyDisplayMode(self.handle))
        return freq

    @property
    def colordepth(self) -> int:
        depth = Quartz.CGDisplayBitsPerPixel(self.handle)
        return depth

    @property
    def brightness(self):
        # display = dm.Display(self.handle)
        # return display.brightness
        return None
        # https://stackoverflow.com/questions/46885603/is-there-a-programmatic-way-to-check-if-brightness-is-at-max-or-min-value-on-osx
        # value = None
        # cmd = """nvram backlight-level | awk '{print $2}'"""
        # err, ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "")
        # if err == 0 and ret:
        #     value = int(float(ret)) * 100
        # return value

    @brightness.setter
    def brightness(self, brightness: int):
        # display = dm.Display(self.handle)
        # try:
        #     display.setBrightness(brightness)
        # except:
        #     pass
        pass
        # https://github.com/thevickypedia/pybrightness/blob/main/pybrightness/controller.py
        # https://eastmanreference.com/complete-list-of-applescript-key-codes
        # for _ in range(32):
        #     os.system("""osascript -e 'tell application "System Events"' -e 'key code 145' -e ' end tell'""")
        # for _ in range(round((32 * int(brightness)) / 100)):
        #     os.system("""osascript -e 'tell application "System Events"' -e 'key code 144' -e ' end tell'""")

    @property
    def contrast(self):
        # https://github.com/jonls/redshift/blob/master/src/gamma-quartz.c
        # raise NotImplementedError
        return None

    @contrast.setter
    def contrast(self, contrast: float):
        # Decrease display contrast: Command+Option+Control-
        # Increase display contrast: Command+Option+Control+
        # raise NotImplementedError
        pass

    @property
    def mode(self) -> Optional[DisplayMode]:
        mode = Quartz.CGDisplayCopyDisplayMode(self.handle)
        w = Quartz.CGDisplayModeGetWidth(mode)
        h = Quartz.CGDisplayModeGetHeight(mode)
        r = Quartz.CGDisplayModeGetRefreshRate(mode)
        res = DisplayMode(w, h, r)
        return res

    @mode.setter
    def mode(self, mode: DisplayMode):
        # https://stackoverflow.com/questions/10596489/programmatically-change-resolution-os-x
        allModes = Quartz.CGDisplayCopyAllDisplayModes(self.handle, None)
        for m in allModes:
            w = Quartz.CGDisplayModeGetWidth(m)
            h = Quartz.CGDisplayModeGetHeight(m)
            r = Quartz.CGDisplayModeGetRefreshRate(m)
            if w == mode.width and h == mode.height and r == mode.frequency:
                # This is simpler, but has a temporary effect:
                # Quartz.CGDisplaySetDisplayMode(displayId, m, None)
                ret, configRef = Quartz.CGBeginDisplayConfiguration(None)
                if not ret:
                    ret = Quartz.CGConfigureDisplayWithDisplayMode(configRef, self.handle, m, None)
                    if not ret:
                        Quartz.CGCompleteDisplayConfiguration(configRef, Quartz.kCGConfigurePermanently)
                    else:
                        Quartz.CGCancelDisplayConfiguration(configRef)
                break

    @property
    def defaultMode(self):
        res: Optional[DisplayMode] = None
        modes = Quartz.CGDisplayCopyAllDisplayModes(self.handle,
                                                    {Quartz.kCGDisplayShowDuplicateLowResolutionModes: Quartz.kCFBooleanTrue})
        for mode in modes:
            if bin(Quartz.CGDisplayModeGetIOFlags(mode))[-3] == '1':
                w = Quartz.CGDisplayModeGetWidth(mode)
                h = Quartz.CGDisplayModeGetHeight(mode)
                r = Quartz.CGDisplayModeGetRefreshRate(mode)
                res = DisplayMode(w, h, r)
                break
        return res

    def setDefaultMode(self):
        defMode = self.defaultMode
        if defMode:
            self.mode = defMode

    @property
    def allModes(self) -> List[DisplayMode]:
        modes: List[DisplayMode] = []
        allModes = Quartz.CGDisplayCopyAllDisplayModes(self.handle, None)
        for mode in allModes:
            w = Quartz.CGDisplayModeGetWidth(mode)
            h = Quartz.CGDisplayModeGetHeight(mode)
            r = Quartz.CGDisplayModeGetRefreshRate(mode)
            modes.append(DisplayMode(w, h, r))
        return modes

    @property
    def isPrimary(self):
        return self.name == _getName(Quartz.CGMainDisplayID())

    def setPrimary(self):
        # https://stackoverflow.com/questions/13722508/change-main-monitor-on-mac-programmatically#:~:text=To%20change%20the%20secondary%20monitor%20to%20be%20the,%28%29.%20A%20full%20sample%20can%20be%20found%20Here
        self.setPosition(PRIMARY, "")

    def turnOn(self):
        # This works, but won't wake up the display

        def mouseEvent(eventType, posx, posy):
            theEvent = CG.CGEventCreateMouseEvent(None, eventType, CG.CGPointMake(posx, posy), CG.kCGMouseButtonLeft)
            CG.CGEventSetType(theEvent, eventType)
            # or kCGSessionEventTap?
            CG.CGEventPost(CG.kCGHIDEventTap, theEvent)
            # CG.CFRelease(theEvent)   # Produces a Hardware error?!?!?!

        def mousemove(posx, posy):
            mouseEvent(CG.kCGEventMouseMoved, posx, posy)

        def mouseclick(posx, posy):
            # Not necessary to previously move the mouse to given location
            # mouseEvent(CG.kCGEventMouseMoved, posx, posy)
            mouseEvent(CG.kCGEventLeftMouseDown, posx, posy)
            time.sleep(0.1)
            mouseEvent(CG.kCGEventLeftMouseUp, posx, posy)

        # mousemove(200, 200)
        mouseclick(200, 200)

        # This won't wake up monitor either (refers to the whole system)
        # cmd = """pmset wake"""
        # subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)

    def turnOff(self):
        # https://stackoverflow.com/questions/16402672/control-screen-with-python
        # self.suspend()
        # raise NotImplementedError
        pass

    def suspend(self):
        cmd = """pmset displaysleepnow"""
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)

    @property
    def isOn(self):
        # raise NotImplementedError
        return False

    def attach(self, width: int = 0, height: int = 0):
        # raise NotImplementedError
        pass

    def detach(self, permanent: bool = False):
        # Maybe manipulating position and/or size?
        # raise NotImplementedError
        pass

    @property
    def isAttached(self):
        return self.name in _NSgetAllMonitorsDict().keys()


def _setPosition(relativePos: Union[int, Position], relativeTo: str, name: str):
    monitors = _NSgetAllMonitorsDict()
    if name in monitors.keys() and relativeTo in monitors.keys():

        frame = monitors[name]["screen"].frame()
        targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                     "pos": Point(frame.origin.x, frame.origin.y),
                     "size": Point(frame.size.width, frame.size.height)}

        frame = monitors[relativeTo]["screen"].frame()
        relMon = {"pos": Point(frame.origin.x, frame.origin.y),
                  "size": Point(frame.size.width, frame.size.height)}

        x, y, relCmd = _getRelativePosition(targetMon, relMon)
        ret, configRef = Quartz.CGBeginDisplayConfiguration(None)
        # If this display becomes primary (0, 0). MUST reposition primary monitor first!
        if not ret:
            ret = Quartz.CGConfigureDisplayOrigin(configRef, monitors[name]["displayId"], x, y)
            if not ret:
                Quartz.CGCompleteDisplayConfiguration(configRef, Quartz.kCGConfigurePermanently)
            else:
                Quartz.CGCancelDisplayConfiguration(configRef)
        # https://apple.stackexchange.com/questions/249447/change-display-arrangement-in-os-x-macos-programmatically
        # https://github.com/univ-of-utah-marriott-library-apple/display_manager/blob/stable/README.md


def _getName(displayId: int):
    screen = AppKit.NSScreen.mainScreen()
    try:
        scrName = screen.localizedName() + "_" + str(displayId)
    except:
        # In older macOS, screen doesn't have localizedName() method
        scrName = "Display" + "_" + str(displayId)
    return scrName


def _NSgetAllMonitors():
    monitors = []
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        scrName = _getName(displayId)
        monitors.append([screen, desc, displayId, scrName])
    return monitors


def _NSgetAllMonitorsDict():
    monitors = {}
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        scrName = _getName(displayId)
        monitors[scrName] = {"screen": screen, "desc": desc, "displayId": displayId}
    return monitors


def _NSgetMonitor(name: str):
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        scrName = _getName(displayId)

        if scrName == name:
            return [screen, desc, displayId, scrName]
    return None


def _NSgetDisplayId(name: str = ""):
    displayId: int = 0
    if name:
        mon = _NSgetMonitor(name)
        if mon:
            screen, desc, displayId, scrName = mon
            displayId = desc['NSScreenNumber']
    else:
        displayId = Quartz.CGMainDisplayID()
    return int(displayId)


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
