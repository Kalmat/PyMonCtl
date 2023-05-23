#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import threading

import win32evtlog

assert sys.platform == "win32"

import ctypes
import pywintypes
from typing import Optional, List
import win32api
import win32con

from pymonctl import Structs


dpiAware = ctypes.windll.user32.GetAwarenessFromDpiAwarenessContext(ctypes.windll.user32.GetThreadDpiAwarenessContext())
if dpiAware == 0:
    # It seems that this can't be invoked twice. Setting it to 2 for apps having 0 (unaware) may have less impact
    ctypes.windll.shcore.SetProcessDpiAwareness(2)


def __getAllMonitors(name: str = ""):
    for monitor in win32api.EnumDisplayMonitors():
        hMon = monitor[0].handle
        monitorInfo = win32api.GetMonitorInfo(hMon)
        if not name or (name and monitorInfo.get("Device", "") == name):
            yield [hMon, monitorInfo]


def _getAllScreens() -> dict[str, Structs.ScreenValue]:
    # https://stackoverflow.com/questions/35814309/winapi-changedisplaysettingsex-does-not-work
    result: dict[str, Structs.ScreenValue] = {}
    monitors = win32api.EnumDisplayMonitors()
    i = 0
    while True:
        try:
            dev = win32api.EnumDisplayDevices(None, i, 0)
        except:
            break

        if dev.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            # Device content: http://timgolden.me.uk/pywin32-docs/PyDISPLAY_DEVICE.html
            # Settings content: http://timgolden.me.uk/pywin32-docs/PyDEVMODE.html
            monitorInfo = None
            monitor = None
            for mon in monitors:
                monitor = mon[0].handle
                monitorInfo = win32api.GetMonitorInfo(monitor)
                if monitorInfo.get("Device", "") == dev.DeviceName:
                    break

            if monitorInfo:
                name = dev.DeviceName
                x, y, r, b = monitorInfo.get("Monitor", (0, 0, 0, 0))
                wx, wy, wr, wb = monitorInfo.get("Work", (0, 0, 0, 0))
                is_primary = monitorInfo.get("Flags", 0) == win32con.MONITORINFOF_PRIMARY
                pScale = ctypes.c_uint()
                ctypes.windll.shcore.GetScaleFactorForMonitor(monitor, ctypes.byref(pScale))
                scale = pScale.value
                dpiX = ctypes.c_uint()
                dpiY = ctypes.c_uint()
                ctypes.windll.shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(dpiX), ctypes.byref(dpiY))
                settings = win32api.EnumDisplaySettings(dev.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                rot = settings.DisplayOrientation
                freq = settings.DisplayFrequency
                depth = settings.BitsPerPel

                result[name] = {
                    "id": win32api.MonitorFromPoint((x, y)),
                    "is_primary": is_primary,
                    "pos": Structs.Point(x, y),
                    "size": Structs.Size(abs(r - x), abs(b - y)),
                    "workarea": Structs.Rect(wx, wy, wr, wb),
                    "scale": (scale, scale),
                    "dpi": (dpiX.value, dpiY.value),
                    "orientation": rot,
                    "frequency": freq,
                    "colordepth": depth
                }
        i += 1
    return result


def _getMonitorsCount() -> int:
    return len(win32api.EnumDisplayMonitors())


def _getScreenSize(name: str = "") -> Optional[Structs.Size]:
    size: Optional[Structs.Size] = None
    if name:
        for mon in __getAllMonitors(name):
            monitorInfo = mon[1]
            x, y, r, b = monitorInfo.get("Monitor", (0, 0, 0, 0))
            size = Structs.Size(abs(r - x), abs(b - y))
            break
    else:
        size = Structs.Size(ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))
    return size


def _getWorkArea(name: str = "") -> Optional[Structs.Rect]:
    workarea: Optional[Structs.Rect] = None
    if name:
        for mon in __getAllMonitors(name):
            monitorInfo = mon[1]
            wx, wy, wr, wb = monitorInfo.get("Work", (0, 0, 0, 0))
            # # values seem to be affected by the scale factor of the primary display
            # x, y, r, b = monitorInfo["Monitor"]
            # settings = win32api.EnumDisplaySettings(name, win32con.ENUM_CURRENT_SETTINGS)
            # wr, wb = wx + settings.PelsWidth + (wr - r), wy + settings.PelsHeight + (wb - b)
            workarea = Structs.Rect(wx, wy, wr, wb)
            break
    else:
        monitorInfo = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
        wx, wy, wr, wb = monitorInfo.get("Work", (0, 0, 0, 0))
        workarea = Structs.Rect(wx, wy, wr, wb)
    return workarea


def _getPosition(name: str = "") -> Optional[Structs.Point]:
    pos: Optional[Structs.Point] = None
    if name:
        for mon in __getAllMonitors(name):
            monitorInfo = mon[1]
            x, y, r, b = monitorInfo.get("Monitor", (0, 0, 0, 0))
            pos = Structs.Point(x, y)
            break
    else:
        pos = Structs.Point(0, 0)
    return pos


def _getRect(name: str = "") -> Optional[Structs.Rect]:
    rect: Optional[Structs.Rect] = None
    if name:
        for mon in __getAllMonitors(name):
            monitorInfo = mon[1]
            x, y, r, b = monitorInfo.get("Monitor", (0, 0, 0, 0))
            rect = Structs.Rect(x, y, r, b)
            break
    else:
        rect = Structs.Rect(0, 0, ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))
    return rect


def _findMonitorName(x: int, y: int) -> str:
    # Watch this: started to fail when repeatedly and quickly invoking it in Python 3.10 (it was ok in 3.9)
    monitor = win32api.MonitorFromPoint((x, y))
    monitorInfo = win32api.GetMonitorInfo(monitor)
    name = str(monitorInfo.get("Device", ""))
    return name


def _getCurrentMode(name: str = "") -> Optional[Structs.DisplayMode]:

    if not name:
        winDev = win32api.EnumDisplayDevices(DevNum=0)
        name = winDev.DeviceName

    mode: Optional[Structs.DisplayMode] = None
    try:
        winSettings = win32api.EnumDisplaySettings(name, win32con.ENUM_CURRENT_SETTINGS)
        mode = Structs.DisplayMode(winSettings.PelsWidth, winSettings.PelsHeight, winSettings.DisplayFrequency)
    except:
        pass
    return mode


def _getAllowedModes(name: str = "") -> List[Structs.DisplayMode]:

    if not name:
        winDev = win32api.EnumDisplayDevices(DevNum=0)
        name = winDev.DeviceName

    i = 0
    modes: List[Structs.DisplayMode] = []
    while True:
        try:
            winSettings = win32api.EnumDisplaySettings(name, i)
            mode = Structs.DisplayMode(winSettings.PelsWidth, winSettings.PelsHeight, winSettings.DisplayFrequency)
            if mode not in modes:
                modes.append(mode)
        except:
            break
        i += 1
    return modes


def _changeMode(mode: Structs.DisplayMode, name: str = ""):
    # http://timgolden.me.uk/pywin32-docs/PyDEVMODE.html

    modes = _getAllowedModes(name)

    if mode in modes:
        devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
        devmode.PelsWidth = mode.width
        devmode.PelsHeight = mode.height
        devmode.DisplayFrequency = mode.frequency
        devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT | win32con.DM_DISPLAYFREQUENCY
        if name:
            win32api.ChangeDisplaySettingsEx(name, devmode, 0)
        else:
            win32api.ChangeDisplaySettings(devmode, 0)


def _changeScale(scale: float, name: str = ""):
    devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
    devmode.Scale = scale
    devmode.Fields = win32con.DM_SCALE
    if name:
        win32api.ChangeDisplaySettingsEx(name, devmode, 0)
    else:
        win32api.ChangeDisplaySettings(devmode, 0)


def _changeOrientation(orientation: int, name: str = ""):
    devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
    # win32con.DMDO_DEFAULT = 0, win32con.DMDO_90 = 1, win32con.DMDO_180 = 2, win32con.DMDO_270 = 3
    devmode.DisplayOrientation = orientation
    devmode.Fields = win32con.DM_ORIENTATION
    if name:
        win32api.ChangeDisplaySettingsEx(name, devmode, 0)
    else:
        win32api.ChangeDisplaySettings(devmode, 0)


def _changePosition(newX: int, newY: int, name: str = ""):
    devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
    devmode.Position_x = newX
    devmode.Position_y = newY
    devmode.Fields = win32con.DM_POSITION
    if name:
        win32api.ChangeDisplaySettingsEx(name, devmode, 0)
    else:
        win32api.ChangeDisplaySettings(devmode, 0)


def _eventLoop(kill: threading.Event, interval: float):
    # # https://stackoverflow.com/questions/11219213/read-specific-windows-event-log-event
    server = 'localhost'  # name of the target computer to get event logs
    log_type = 'System'
    handle = win32evtlog.OpenEventLog(server, log_type)
    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    # total = win32evtlog.GetNumberOfEventLogRecords(hand)

    while not kill.is_set():
        events = win32evtlog.ReadEventLog(handle, flags, 0)
        # events_list = [event for event in events if event.EventID == "27035"]
        # events_list = [event for event in events if event.EventType in (2, 4)]
        for event in events:
            # how to hook / filter display changes events ONLY (Microsoft.Win32.DisplaySettingsChanged)?
            print(event.EventID, event.SourceName, event.EventCategory, event.EventType, event.StringInserts)

        kill.wait(interval)

    win32evtlog.CloseEventLog(handle)


def _getMousePos() -> Structs.Point:
    """
    Get the current (x, y) coordinates of the mouse pointer on screen, in pixels

    :return: Point struct
    """
    x, y = win32api.GetCursorPos()
    return Structs.Point(x, y)
