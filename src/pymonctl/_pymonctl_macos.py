#!/usr/bin/python
# -*- coding: utf-8 -*-
# Incomplete type stubs for pyobjc
# mypy: disable_error_code = no-any-return
from __future__ import annotations

import sys
import threading

assert sys.platform == "darwin"

from typing import Optional, List

import AppKit
import Quartz

from pymonctl import Structs, _pointInBox


def __getAllMonitors():
    screens = AppKit.NSScreen.screens()
    screens = [screens[0], screens[0], screens[0], screens[0]]
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        try:
            scrName = screen.localizedName() + "_" + str(displayId)
        except:
            # In older macOS, screen doesn't have localizedName() method
            scrName = "Display" + "_" + str(displayId)

        yield [screen, desc, displayId, scrName]


def __getMonitor(name: str):
    screens = AppKit.NSScreen.screens()
    screens = [screens[0], screens[0], screens[0], screens[0]]
    for screen in screens:
        desc = screen.deviceDescription()
        displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
        try:
            scrName = screen.localizedName() + "_" + str(displayId)
        except:
            # In older macOS, screen doesn't have localizedName() method
            scrName = "Display" + "_" + str(displayId)

        if scrName == name:
            return [screen, desc, displayId, scrName]
    return None


def __getDisplayId(name: str = ""):
    displayId: int = 0
    if name:
        mon = __getMonitor(name)
        if mon:
            screen, desc, displayId, scrName = mon
            displayId = desc['NSScreenNumber']
    else:
        displayId = Quartz.CGMainDisplayID()
    return displayId


def _getAllScreens() -> dict[str, Structs.ScreenValue]:
    result: dict[str, Structs.ScreenValue] = {}
    for mon in __getAllMonitors():
        screen, desc, displayId, scrName = mon

        display = displayId
        is_primary = Quartz.CGDisplayIsMain(display) == 1
        x, y, w, h = int(screen.frame().origin.x), int(screen.frame().origin.y), int(screen.frame().size.width), int(screen.frame().size.height)
        wa = screen.visibleFrame()
        wx, wy, wr, wb = int(wa.origin.x), int(wa.origin.y), int(wa.size.width), int(wa.size.height)
        scale = int(screen.backingScaleFactor() * 100)
        dpi = desc[Quartz.NSDeviceResolution].sizeValue()
        dpiX, dpiY = int(dpi.width), int(dpi.height)
        rot = int(Quartz.CGDisplayRotation(display))
        freq = Quartz.CGDisplayModeGetRefreshRate(Quartz.CGDisplayCopyDisplayMode(display))
        depth = Quartz.CGDisplayBitsPerPixel(display)

        result[scrName] = {
            'id': displayId,
            'is_primary': is_primary,
            'pos': Structs.Point(x, y),
            'size': Structs.Size(w, h),
            'workarea': Structs.Rect(wx, wy, wr, wb),
            'scale': (scale, scale),
            'dpi': (dpiX, dpiY),
            'orientation': rot,
            'frequency': freq,
            'colordepth': depth
        }
    return result


def _getMonitorsCount() -> int:
    return len(AppKit.NSScreen.screens())


def _getScreenSize(name: str = "") -> Optional[Structs.Size]:
    res: Optional[Structs.Size] = None
    size = None
    if name:
        mon = __getMonitor(name)
        if mon:
            screen, desc, displayId, scrName = mon
            size = screen.frame().size
    else:
        size = AppKit.NSScreen.mainScreen().frame().size

    if size:
        res = Structs.Size(int(size.width), int(size.height))
    return res


def _getWorkArea(name: str = "") -> Optional[Structs.Rect]:
    res: Optional[Structs.Rect] = None
    wa = None
    if name:
        mon = __getMonitor(name)
        if mon:
            screen, desc, displayId, scrName = mon
            wa = screen.visibleFrame()
    else:
        wa = AppKit.NSScreen.mainScreen().visibleFrame()

    if wa:
        wx, wy, wr, wb = int(wa.origin.x), int(wa.origin.y), int(wa.size.width), int(wa.size.height)
        res = Structs.Rect(wx, wy, wr, wb)
    return res


def _getPosition(name: str = "") -> Optional[Structs.Point]:
    res: Optional[Structs.Point] = None
    origin = None
    if name:
        mon = __getMonitor(name)
        if mon:
            screen, desc, displayId, scrName = mon
            origin = screen.frame().origin
    else:
        origin = AppKit.NSScreen.mainScreen().frame().origin

    if origin:
        res = Structs.Point(int(origin.x), int(origin.y))
    return res


def _getRect(name: str = "") -> Optional[Structs.Rect]:
    res: Optional[Structs.Rect] = None
    frame = None
    if name:
        mon = __getMonitor(name)
        if mon:
            screen, desc, displayId, scrName = mon
            frame = screen.frame()
    else:
        frame = AppKit.NSScreen.mainScreen().frame()

    if frame:
        res = Structs.Rect(int(frame.origin.x), int(frame.origin.y),
                           int(frame.origin.x) + int(frame.size.width),  int(frame.origin.y) + int(frame.size.height))
    return res


def _findMonitorName(x: int, y: int) -> str:
    name: str = ""
    screens = AppKit.NSScreen.screens()
    for screen in screens:
        frame = screen.frame()
        if _pointInBox(x, y, int(frame.origin.x), int(frame.origin.y), int(frame.size.width), int(frame.size.height)):
            desc = screen.deviceDescription()
            displayId = desc['NSScreenNumber']  # Quartz.NSScreenNumber seems to be wrong
            try:
                name = screen.localizedName() + "_" + str(displayId)
            except:
                # In older macOS, screen doesn't have localizedName() method
                name = "Display" + "_" + str(displayId)
            break
    return name


def _getCurrentMode(name: str = "") -> Optional[Structs.DisplayMode]:
    res: Optional[Structs.DisplayMode] = None
    displayId = __getDisplayId(name)
    if displayId:
        mode = Quartz.CGDisplayCopyDisplayMode(displayId)
        w = Quartz.CGDisplayModeGetWidth(mode)
        h = Quartz.CGDisplayModeGetHeight(mode)
        r = Quartz.CGDisplayModeGetRefreshRate(mode)
        res = Structs.DisplayMode(w, h, r)
    return res


def _getAllowedModes(name: str = "") -> List[Structs.DisplayMode]:
    modes: List[Structs.DisplayMode] = []
    displayId = __getDisplayId(name)
    if displayId:
        allModes = Quartz.CGDisplayCopyAllDisplayModes(displayId, None)
        for mode in allModes:
            w = Quartz.CGDisplayModeGetWidth(mode)
            h = Quartz.CGDisplayModeGetHeight(mode)
            r = Quartz.CGDisplayModeGetRefreshRate(mode)
            modes.append(Structs.DisplayMode(w, h, r))
    return modes


def _changeMode(mode: Structs.DisplayMode, name: str = ""):
    # https://stackoverflow.com/questions/10596489/programmatically-change-resolution-os-x
    displayId = __getDisplayId(name)
    if displayId:
        allModes = Quartz.CGDisplayCopyAllDisplayModes(displayId, None)
        for m in allModes:
            w = Quartz.CGDisplayModeGetWidth(m)
            h = Quartz.CGDisplayModeGetHeight(m)
            r = Quartz.CGDisplayModeGetRefreshRate(m)
            if w == mode.width and h == mode.height and r == mode.frequency:
                Quartz.CGDisplaySetDisplayMode(displayId, m, None)
                break


def _changeScale(scale: int, name: str = ""):
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
    pass


def _changeOrientation(orientation: int, name: str = ""):
    pass


def _changePosition(newX: int, newY: int, name: str = ""):
    displayId = __getDisplayId(name)
    if displayId:
        Quartz.CGConfigureDisplayOrigin(displayId, newX, newY)


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


def _getMousePos(flipValues: bool = False) -> Structs.Point:
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
    return Structs.Point(x, y)
