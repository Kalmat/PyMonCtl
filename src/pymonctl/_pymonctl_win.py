#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
assert sys.platform == "win32"

import threading

import ctypes
import ctypes.wintypes
import pywintypes
from typing import Optional, List, Union, Tuple, cast
import win32api
import win32con
import win32evtlog
import win32gui

from pymonctl import BaseMonitor, getAllMonitorsDict, _getRelativePosition
from .structs import *


dpiAware = ctypes.windll.user32.GetAwarenessFromDpiAwarenessContext(ctypes.windll.user32.GetThreadDpiAwarenessContext())
if dpiAware == 0:
    # It seems that this can't be invoked twice. Setting it to 2 for apps having 0 (unaware) may have less impact
    ctypes.windll.shcore.SetProcessDpiAwareness(2)


def _getAllMonitors() -> list[Monitor]:
    monitors: list[Monitor] = []
    for monitor in win32api.EnumDisplayMonitors():
        monitors.append(Monitor(monitor[0].handle))
    return monitors


def _getAllMonitorsDict() -> dict[str, ScreenValue]:
    # https://stackoverflow.com/questions/35814309/winapi-changedisplaysettingsex-does-not-work
    result: dict[str, ScreenValue] = {}
    monitors = win32api.EnumDisplayMonitors()
    for monitor in monitors:
        hMon = monitor[0].handle
        monitorInfo = win32api.GetMonitorInfo(hMon)
        monName = monitorInfo.get("Device", "")

        dev = None
        try:
            # Device content: http://timgolden.me.uk/pywin32-docs/PyDISPLAY_DEVICE.html
            dev = win32api.EnumDisplayDevices(monName, 0, 0)
        except:
            pass
        if dev and dev.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            name = monName
            x, y, r, b = monitorInfo.get("Monitor", (-1, -1, 0, 0))
            wx, wy, wr, wb = monitorInfo.get("Work", (-1, -1, 0, 0))
            is_primary = monitorInfo.get("Flags", 0) == win32con.MONITORINFOF_PRIMARY
            pScale = ctypes.c_uint()
            ctypes.windll.shcore.GetScaleFactorForMonitor(hMon, ctypes.byref(pScale))
            scale = pScale.value
            dpiX = ctypes.c_uint()
            dpiY = ctypes.c_uint()
            ctypes.windll.shcore.GetDpiForMonitor(hMon, 0, ctypes.byref(dpiX), ctypes.byref(dpiY))
            # Settings content: http://timgolden.me.uk/pywin32-docs/PyDEVMODE.html
            settings = win32api.EnumDisplaySettings(monName, win32con.ENUM_CURRENT_SETTINGS)
            rot = settings.DisplayOrientation
            freq = settings.DisplayFrequency
            depth = settings.BitsPerPel

            result[name] = {
                "system_name": name,
                "handle": win32api.MonitorFromPoint((x, y)),
                "is_primary": is_primary,
                "position": Point(x, y),
                "size": Size(abs(r - x), abs(b - y)),
                "workarea": Rect(wx, wy, wr, wb),
                "scale": (scale, scale),
                "dpi": (dpiX.value, dpiY.value),
                "orientation": rot,
                "frequency": freq,
                "colordepth": depth
            }
    return result


def _getMonitorsCount() -> int:
    return len(win32api.EnumDisplayMonitors())


def _findMonitor(x: int, y: int) -> Optional[Monitor]:
    # Watch this: started to fail when repeatedly and quickly invoking it in Python 3.10 (it was ok in 3.9)
    hMon = win32api.MonitorFromPoint((x, y), win32con.MONITOR_DEFAULTTONEAREST)
    if hMon:
        return Monitor(hMon)
    return None


def _getPrimary() -> Monitor:
    return Monitor()


def _arrangeMonitors(arrangement: dict[str, dict[str, Union[str, int, Position, Point, Size]]]):
    # https://stackoverflow.com/questions/35814309/winapi-changedisplaysettingsex-does-not-work
    # https://stackoverflow.com/questions/195267/use-windows-api-from-c-sharp-to-set-primary-monitor
    monitors = _win32getAllMonitorsDict()
    for monName in monitors.keys():
        if monName not in arrangement.keys():
            return
    primaryPresent = False
    for monName in arrangement.keys():
        relPos = arrangement[monName]["relativePos"]
        relMon = arrangement[monName]["relativeTo"]
        if monName not in monitors.keys() or (relMon and relMon not in monitors.keys()) or \
                (not relMon and relPos != PRIMARY):
            return
        elif relPos == PRIMARY:
            primaryPresent = True
    if not primaryPresent:
        return

    targetArrangement: dict[str, dict[str, Union[str, int, Position, Point, Size]]] = {}
    i = len(arrangement)
    while len(arrangement) > len(targetArrangement) and i >= 0:

        for monName in arrangement.keys():

            relPos = arrangement[monName]["relativePos"]
            relMon = arrangement[monName]["relativeTo"]

            if monName not in targetArrangement.keys() and \
                    (relMon in targetArrangement.keys() or relPos == PRIMARY):
                monInfo = monitors[monName]["monitor"]
                x, y, r, b = monInfo.get("Monitor", (-1, -1, 0, 0))
                w = abs(r - x)
                h = abs(b - y)
                arrangement[monName]["position"] = Point(x, y)
                arrangement[monName]["size"] = Size(w, h)
                targetArrangement[monName] = arrangement[monName]
                x, y, _ = _getRelativePosition(arrangement[str(monName)], targetArrangement[str(relMon)] if relMon else None)
                targetArrangement[monName]["position"] = Point(x, y)
                break
        i -= 1

    for monName in targetArrangement.keys():
        devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
        x, y = cast(Point, targetArrangement[monName]["position"])
        if x == 0 and y == 0:
            flags = win32con.CDS_SET_PRIMARY | win32con.CDS_UPDATEREGISTRY | win32con.CDS_NORESET
        else:
            flags = win32con.CDS_UPDATEREGISTRY | win32con.CDS_NORESET
        devmode.Position_x = x
        devmode.Position_y = y
        devmode.Fields = win32con.DM_POSITION
        win32api.ChangeDisplaySettingsEx(monName, devmode, flags)

    # Not using setPosition() because we need to first request all changes, then execute this with NULL params
    win32api.ChangeDisplaySettingsEx()


def _getMousePos() -> Point:
    x, y = win32api.GetCursorPos()
    return Point(x, y)


class Monitor(BaseMonitor):

    def __init__(self, handle: Optional[int] = None):
        """
        Class to access all methods and functions to get info and manage monitors plugged to the system.

        This class is not meant to be directly instantiated. Instead, use convenience functions like getAllMonitors(),
        getPrimary() or findMonitor(x, y).
        """
        if not handle:
            handle = win32api.MonitorFromPoint((0, 0), win32con.MONITOR_DEFAULTTOPRIMARY)
        self.handle = handle
        monitorInfo = win32api.GetMonitorInfo(handle)
        self.name = monitorInfo.get("Device", "")

    @property
    def size(self) -> Optional[Size]:
        monitorInfo = win32api.GetMonitorInfo(self.handle)
        if monitorInfo:
            x, y, r, b = monitorInfo.get("Monitor", (-1, -1, 0, 0))
            return Size(abs(r - x), abs(b - y))
        return None

    @property
    def workarea(self) -> Optional[Rect]:
        monitorInfo = win32api.GetMonitorInfo(self.handle)
        if monitorInfo:
            wx, wy, wr, wb = monitorInfo.get("Work", (-1, -1, 0, 0))
            return Rect(wx, wy, wr, wb)
        return None

    @property
    def position(self) -> Optional[Point]:
        monitorInfo = win32api.GetMonitorInfo(self.handle)
        if monitorInfo:
            x, y, r, b = monitorInfo.get("Monitor", (-1, -1, 0, 0))
            return Point(x, y)
        return None

    def setPosition(self, relativePos: Union[int, Position], relativeTo: Optional[str]):
        # https://stackoverflow.com/questions/35814309/winapi-changedisplaysettingsex-does-not-work
        # https://stackoverflow.com/questions/195267/use-windows-api-from-c-sharp-to-set-primary-monitor
        if relativePos == PRIMARY:
            self.setPrimary()

        else:
            monitors = _win32getAllMonitorsDict()
            if self.name in monitors.keys() and relativeTo in monitors.keys():
                targetMonInfo = monitors[self.name]["monitor"]
                x, y, r, b = targetMonInfo.get("Monitor", (-1, -1, 0, 0))
                w = abs(r - x)
                h = abs(b - y)
                targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                             "position": Point(x, y), "size": Size(w, h)}

                relMonInfo = monitors[relativeTo]["monitor"]
                x, y, r, b = relMonInfo.get("Monitor", (-1, -1, 0, 0))
                w = abs(r - x)
                h = abs(b - y)
                relMon = {"position": Point(x, y), "size": Size(w, h)}
                x, y, _ = _getRelativePosition(targetMon, relMon)

                devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
                devmode.Position_x = x
                devmode.Position_y = y
                flags = win32con.CDS_UPDATEREGISTRY | win32con.CDS_NORESET
                devmode.Fields = win32con.DM_POSITION
                win32api.ChangeDisplaySettingsEx(self.name, devmode, flags)
                win32api.ChangeDisplaySettingsEx()

    @property
    def box(self) -> Optional[Box]:
        monitorInfo = win32api.GetMonitorInfo(self.handle)
        if monitorInfo:
            x, y, r, b = monitorInfo.get("Monitor", (-1, -1, 0, 0))
            return Box(x, y, abs(r - x), abs(b - y))
        return None

    @property
    def rect(self) -> Optional[Rect]:
        monitorInfo = win32api.GetMonitorInfo(self.handle)
        if monitorInfo:
            x, y, r, b = monitorInfo.get("Monitor", (-1, -1, 0, 0))
            return Rect(x, y, r, b)
        return None

    @property
    def scale(self) -> float:
        pScale = ctypes.c_uint()
        ctypes.windll.shcore.GetScaleFactorForMonitor(self.handle, ctypes.byref(pScale))
        return pScale.value

    @scale.setter
    def scale(self, scale: float):
        devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
        devmode.Scale = scale
        devmode.Fields = win32con.DM_SCALE
        win32api.ChangeDisplaySettingsEx(self.name, devmode, 0)

    @property
    def dpi(self) -> Tuple[float, float]:
        dpiX = ctypes.c_uint()
        dpiY = ctypes.c_uint()
        ctypes.windll.shcore.GetDpiForMonitor(self.handle, 0, ctypes.byref(dpiX), ctypes.byref(dpiY))
        return dpiX.value, dpiY.value

    @property
    def orientation(self) -> Optional[Union[int, Orientation]]:
        # Settings content: http://timgolden.me.uk/pywin32-docs/PyDEVMODE.html
        settings = win32api.EnumDisplaySettings(self.name, win32con.ENUM_CURRENT_SETTINGS)
        if settings:
            return settings.DisplayOrientation
        return None

    @orientation.setter
    def orientation(self, orientation: Orientation):
        if orientation in (NORMAL, INVERTED, LEFT, RIGHT):
            devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
            devmode.DisplayOrientation = orientation
            devmode.Fields = win32con.DM_ORIENTATION
            win32api.ChangeDisplaySettingsEx(self.name, devmode, 0)

    @property
    def frequency(self) -> Optional[float]:
        settings = win32api.EnumDisplaySettings(self.name, win32con.ENUM_CURRENT_SETTINGS)
        if settings:
            return settings.DisplayFrequency
        return None
    refreshRate = frequency

    @property
    def colordepth(self) -> Optional[int]:
        settings = win32api.EnumDisplaySettings(self.name, win32con.ENUM_CURRENT_SETTINGS)
        if settings:
            return settings.BitsPerPel
        return None

    @property
    def brightness(self) -> Optional[int]:
        minBright = ctypes.c_uint()
        currBright = ctypes.c_uint()
        maxBright = ctypes.c_uint()
        hDevices = _win32getPhysicalMonitorsHandles(self.handle)
        for hDevice in hDevices:
            ctypes.windll.dxva2.GetMonitorBrightness(hDevice, ctypes.byref(minBright), ctypes.byref(currBright),
                                                     ctypes.byref(maxBright))
            _win32destroyPhysicalMonitors(hDevices)
            normBrightness = (currBright.value / ((maxBright.value + minBright.value) or 1)) * 100
            return normBrightness
        return None

    @brightness.setter
    def brightness(self, brightness: int):
        minBright = ctypes.c_uint()
        currBright = ctypes.c_uint()
        maxBright = ctypes.c_uint()
        hDevices = _win32getPhysicalMonitorsHandles(self.handle)
        for hDevice in hDevices:
            ctypes.windll.dxva2.GetMonitorBrightness(hDevice, ctypes.byref(minBright), ctypes.byref(currBright),
                                                     ctypes.byref(maxBright))
            normBrightness = brightness * ((maxBright.value + minBright.value) / 100)
            if minBright.value <= brightness <= maxBright.value and currBright.value != brightness:
                ctypes.windll.dxva2.SeetMonitorBrightness(hDevice, normBrightness)
            ctypes.windll.dxva2.DestroyPhysicalMonitor(hDevice)

    @property
    def contrast(self) -> Optional[int]:
        minCont = ctypes.c_uint()
        currCont = ctypes.c_uint()
        maxCont = ctypes.c_uint()
        hDevices = _win32getPhysicalMonitorsHandles(self.handle)
        for hDevice in hDevices:
            ctypes.windll.dxva2.GetMonitorContrast(hDevice, ctypes.byref(minCont), ctypes.byref(currCont),
                                                   ctypes.byref(maxCont))
            _win32destroyPhysicalMonitors(hDevices)
            normContrast = (currCont.value / ((maxCont.value + minCont.value) or 1)) * 100
            return normContrast
        return None

    @contrast.setter
    def contrast(self, contrast: int):
        minCont = ctypes.c_uint()
        currCont = ctypes.c_uint()
        maxCont = ctypes.c_uint()
        hDevices = _win32getPhysicalMonitorsHandles(self.handle)
        for hDevice in hDevices:
            ctypes.windll.dxva2.GetMonitorContrast(hDevice, ctypes.byref(minCont), ctypes.byref(currCont),
                                                   ctypes.byref(maxCont))
            normContrast = contrast * ((maxCont.value + minCont.value) / 100)
            if minCont.value <= contrast <= maxCont.value and currCont.value != contrast:
                ctypes.windll.dxva2.SeetMonitorContrast(hDevice, normContrast)
            ctypes.windll.dxva2.DestroyPhysicalMonitor(hDevice)

    @property
    def mode(self) -> DisplayMode:
        winSettings = win32api.EnumDisplaySettings(self.name, win32con.ENUM_CURRENT_SETTINGS)
        return DisplayMode(winSettings.PelsWidth, winSettings.PelsHeight, winSettings.DisplayFrequency)

    @mode.setter
    def mode(self, mode: DisplayMode):
        devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
        devmode.PelsWidth = mode.width
        devmode.PelsHeight = mode.height
        devmode.DisplayFrequency = mode.frequency
        devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT | win32con.DM_DISPLAYFREQUENCY
        win32api.ChangeDisplaySettingsEx(self.name, devmode, 0)

    @property
    def defaultMode(self) -> DisplayMode:
        settings = win32api.EnumDisplaySettings(self.name, win32con.ENUM_REGISTRY_SETTINGS)
        return DisplayMode(settings.PelsWidth, settings.PelsHeight, settings.DisplayFrequency)

    def setDefaultMode(self):
        defMode = self.defaultMode
        if defMode:
            self.mode = defMode

    @property
    def allModes(self) -> list[DisplayMode]:
        i = 0
        modes: List[DisplayMode] = []
        while True:
            try:
                winSettings = win32api.EnumDisplaySettings(self.name, i)
                mode = DisplayMode(winSettings.PelsWidth, winSettings.PelsHeight, winSettings.DisplayFrequency)
                if mode not in modes:
                    modes.append(mode)
            except:
                break
            i += 1
        return modes

    @property
    def isPrimary(self) -> bool:
        return self.position == Point(0, 0)

    def setPrimary(self):
        if not self.isPrimary:
            monitors = _win32getAllMonitorsDict()
            if len(monitors.keys()) > 1:
                xOffset = 0
                yOffset = 0
                for monName in monitors.keys():
                    monInfo = monitors[monName]["monitor"]
                    if monName == self.name:
                        xOffset = monInfo["Monitor"][0]
                        yOffset = monInfo["Monitor"][1]
                        if monInfo.get("Flags", 0) == win32con.MONITORINFOF_PRIMARY:
                            return
                        else:
                            devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
                            devmode.Fields = win32con.DM_POSITION
                            devmode.Position_x = 0
                            devmode.Position_y = 0
                            flags = win32con.CDS_SET_PRIMARY | win32con.CDS_UPDATEREGISTRY | win32con.CDS_NORESET
                            win32api.ChangeDisplaySettingsEx(self.name, devmode, flags)
                            break

                flags = win32con.CDS_UPDATEREGISTRY | win32con.CDS_NORESET
                for monName in monitors.keys():
                    monInfo = monitors[monName]["monitor"]
                    if monName != self.name:
                        x = monInfo["Monitor"][0] - xOffset
                        y = monInfo["Monitor"][1] - yOffset
                        devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
                        devmode.Fields = win32con.DM_POSITION
                        devmode.Position_x = x
                        devmode.Position_y = y
                        win32api.ChangeDisplaySettingsEx(monName, devmode, flags)
                win32api.ChangeDisplaySettingsEx()

    def turnOn(self):
        # https://stackoverflow.com/questions/16402672/control-screen-with-python
        if _win32hasVCPSupport(self.handle) and _win32hasVCPPowerSupport(self.handle):
            if not self.isOn:
                hDevices = _win32getPhysicalMonitorsHandles(self.handle)
                for hDevice in hDevices:
                    # code and value according to: VESA Monitor Control Command Set (MCCS) standard, version 1.0 and 2.0.
                    ctypes.windll.dxva2.SetVCPFeature(hDevice, 0xD6, 0x01)
                    ctypes.windll.dxva2.DestroyPhysicalMonitor(hDevice)
        else:
            # This will not work in modern systems. A mouse move can do the trick (for ALL monitors)
            # win32gui.SendMessage(win32console.GetConsoleWindow(), win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, -1)
            mx, my = _getMousePos()
            _win32moveMouse(mx + 1, my + 1)
            _win32moveMouse(mx, my)

    def turnOff(self):
        # https://stackoverflow.com/questions/16402672/control-screen-with-python
        if _win32hasVCPSupport(self.handle) and _win32hasVCPPowerSupport(self.handle):
            if self.isOn:
                hDevices = _win32getPhysicalMonitorsHandles(self.handle)
                for hDevice in hDevices:
                    # code and value according to: VESA Monitor Control Command Set (MCCS) standard, version 1.0 and 2.0.
                    ctypes.windll.dxva2.SetVCPFeature(hDevice, 0xD6, 0x05)
                    ctypes.windll.dxva2.DestroyPhysicalMonitor(hDevice)
        else:
            # win32console.GetConsoleWindow() / win32con.HWND_BROADCAST -> Will turn on/off ALL monitors
            # hMon / hDevice won't work
            win32gui.SendMessageTimeout(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, 2,
                                        win32con.SMTO_ABORTIFHUNG, 100)

    def suspend(self):
        if _win32hasVCPSupport(self.handle) and _win32hasVCPPowerSupport(self.handle):
            hDevices = _win32getPhysicalMonitorsHandles(self.handle)
            for hDevice in hDevices:
                # code and value according to: VESA Monitor Control Command Set (MCCS) standard, version 1.0 and 2.0.
                ctypes.windll.dxva2.SetVCPFeature(hDevice, 0xD6, 0x04)
                ctypes.windll.dxva2.DestroyPhysicalMonitor(hDevice)
        else:
            # win32console.GetConsoleWindow() / win32con.HWND_BROADCAST -> Will turn on/off ALL monitors
            # hMon / hDevice won't work
            win32gui.SendMessageTimeout(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, 1,
                                        win32con.SMTO_ABORTIFHUNG, 100)

    @property
    def isOn(self) -> Optional[bool]:
        ret = None
        if _win32hasVCPSupport(self.handle) and _win32hasVCPPowerSupport(self.handle):
            hDevices = _win32getPhysicalMonitorsHandles(self.handle)
            for hDevice in hDevices:
                # code and value according to: VESA Monitor Control Command Set (MCCS) standard, version 1.0 and 2.0.
                pvct = ctypes.c_uint()
                currValue = ctypes.c_uint()
                maxValue = ctypes.c_uint()
                ctypes.windll.dxva2.GetVCPFeatureAndVCPFeatureReply(hDevice, 0xD6, ctypes.byref(pvct),
                                                                    ctypes.byref(currValue), ctypes.byref(maxValue))
                ret = currValue.value == 1
            _win32destroyPhysicalMonitors(hDevices)
        else:
            # Not working by now (tried with hDevice as well)
            # https://stackoverflow.com/questions/203355/is-there-any-way-to-detect-the-monitor-state-in-windows-on-or-off
            # https://learn.microsoft.com/en-us/windows/win32/power/power-management-functions
            is_working = ctypes.c_uint()
            res = ctypes.windll.kernel32.GetDevicePowerState(self.handle, ctypes.byref(is_working))
            if res:
                ret = bool(is_working.value == 1)
        return ret

    def attach(self):
        dev = win32api.EnumDisplayDevices(self.name, 0, 0)
        settings = win32api.EnumDisplaySettings(self.name, win32con.ENUM_REGISTRY_SETTINGS)
        width, height = self.size or 0, 0
        if width == 0 or height == 0:
            width = settings.PelsWidth
            height = settings.PelsHeight
        if width != 0 and height != 0 and not dev.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
            devmode.PelsWidth = width
            devmode.PelsHeight = height
            devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
            win32api.ChangeDisplaySettingsEx(self.name, devmode, win32con.CDS_UPDATEREGISTRY)

    def detach(self, permanent: bool = False):
        dev = win32api.EnumDisplayDevices(self.name, 0, 0)
        if dev.StateFlags & win32con.DISPLAY_DEVICE_ATTACHED_TO_DESKTOP:
            devmode = pywintypes.DEVMODEType()  # type: ignore[attr-defined]
            devmode.PelsWidth = 0
            devmode.PelsHeight = 0
            devmode.Position_x = 0
            devmode.Position_y = 0
            devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT | win32con.DM_POSITION
            win32api.ChangeDisplaySettingsEx(self.name, devmode, win32con.CDS_UPDATEREGISTRY if permanent else 0)

    @property
    def isAttached(self) -> Optional[bool]:
        return self.name in getAllMonitorsDict().keys()


def _win32getAllMonitorsDict():
    monitors = {}
    for monitor in win32api.EnumDisplayMonitors():
        hMon = monitor[0].handle
        monitorInfo = win32api.GetMonitorInfo(hMon)
        monitors[monitorInfo.get("Device", "")] = {"hMon": hMon, "monitor": monitorInfo}
    return monitors


def _win32getPhysicalMonitorsHandles(hMon):
    # https://stackoverflow.com/questions/60580536/changing-monitor-input-source-programmatically

    class _PHYSICAL_MONITOR(ctypes.Structure):
        _fields_ = [('handle', ctypes.wintypes.HANDLE),
                    ('description', ctypes.wintypes.WCHAR * 128)]

    handles = []
    count = ctypes.wintypes.DWORD()
    ret = ctypes.windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(hMon, ctypes.byref(count))
    if ret and count.value > 0:
        physical_array = (_PHYSICAL_MONITOR * count.value)()
        ret = ctypes.windll.dxva2.GetPhysicalMonitorsFromHMONITOR(hMon, count.value, physical_array)
        if ret:
            for physical in physical_array:
                handles.append(physical.handle)
    return handles


def _win32destroyPhysicalMonitors(hDevices):
    for hDevice in hDevices:
        try:
            ctypes.windll.dxva2.DestroyPhysicalMonitor(hDevice)
        except:
            pass


def _win32moveMouse(x: int, y: int, click: bool = False):
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, x, y)
    if click:
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)


def _win32hasVCPSupport(handle: int):
    # https://github.com/dot-osk/monitor_ctrl/blob/master/vcp.py
    # https://github.com/newAM/monitorcontrol/blob/main/monitorcontrol/vcp
    ret = False
    hDevices = _win32getPhysicalMonitorsHandles(handle)
    for hDevice in hDevices:
        size = ctypes.wintypes.DWORD()
        ret = ctypes.windll.dxva2.GetCapabilitiesStringLength(hDevice, ctypes.byref(size))
        if ret and size.value > 0:
            ret = True
            break
    _win32destroyPhysicalMonitors(hDevices)
    return ret


def _win32getVCPCapabilities(handle: int):
    # https://github.com/dot-osk/monitor_ctrl/blob/master/vcp.py
    # https://www.ddcutil.com/monitor_notes/
    ret = ""
    hDevices = _win32getPhysicalMonitorsHandles(handle)
    for hDevice in hDevices:
        size = ctypes.wintypes.DWORD()
        res = ctypes.windll.dxva2.GetCapabilitiesStringLength(hDevice, ctypes.byref(size))
        if res and size.value > 0:
            capabilities = (ctypes.c_char * size.value)()
            res = ctypes.windll.dxva2.CapabilitiesRequestAndCapabilitiesReply(hDevice, capabilities, size)
            if res:
                ret = capabilities.value.decode('ASCII')
        break
    _win32destroyPhysicalMonitors(hDevices)
    return ret


def _win32hasVCPPowerSupport(handle: int):
    return "D6(" in _win32getVCPCapabilities(handle)


def _eventLoop(kill: threading.Event, interval: float):
    # https://stackoverflow.com/questions/48720924/python-3-detect-monitor-power-state-in-windows
    # https://wiki.wxpython.org/HookingTheWndProc
    # https://stackoverflow.com/questions/48720924/python-3-detect-monitor-power-state-in-windows
    # https://stackoverflow.com/questions/4273252/detect-inserted-usb-on-windows

    class NotificationWindow:

        def __init__(self):
            hinst = win32api.GetModuleHandle(None)
            wndclass = win32gui.WNDCLASS()
            wndclass.hInstance = hinst  # type: ignore[misc]
            wndclass.lpszClassName = "NotificationLoopWindowClass"  # type: ignore[misc]
            CMPFUNC = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p)
            wndproc_pointer = CMPFUNC(self.MyWndProc)
            wndclass.lpfnWndProc = {win32con.WM_POWERBROADCAST: wndproc_pointer}  # type: ignore[misc]

            myWindowClass = win32gui.RegisterClass(wndclass)
            hwnd = win32gui.CreateWindowEx(win32con.WS_EX_LEFT,
                                           myWindowClass,  # type: ignore[misc, arg-type]
                                           "NotificationLoopMsgWindow",
                                           0,
                                           0,
                                           0,
                                           win32con.CW_USEDEFAULT,
                                           win32con.CW_USEDEFAULT,
                                           0,
                                           0,
                                           hinst,
                                           None)
            self.hWnd = hwnd

            # Set the WndProc to our function
            self.oldWndProc = win32gui.SetWindowLong(self.hWnd, win32con.GWL_WNDPROC, self.MyWndProc)

            # Make a dictionary of message names to be used for printing below
            self.msgdict = {}
            for name in dir(win32con):
                if name.startswith("WM_"):
                    value = getattr(win32con, name)
                    self.msgdict[value] = name

        def MyWndProc(self, hWnd, msg, wParam, lParam):

            # Is this necessary since the window is going away?
            # if msg == win32con.WM_DESTROY:
            #     # Set back the WndProc to original function
            #     win32api.SetWindowLong(self.hWnd, win32con.GWL_WNDPROC, self.oldWndProc)
            if msg == win32con.WM_DISPLAYCHANGE:
                print("DISPLAY CHANGE:", self.msgdict.get(msg), hWnd, msg, wParam, lParam)
            else:
                print("OTHER:", self.msgdict.get(msg), hWnd, msg, wParam, lParam)

            return win32gui.CallWindowProc(self.oldWndProc, hWnd, msg, wParam, lParam)

    win = NotificationWindow()
    while not kill.is_set():
        win32gui.PumpWaitingMessages()
        kill.wait(interval)
    win32gui.PostMessage(win.hWnd, win32con.WM_CLOSE, 0, 0)


def _eventLogLoop(kill: threading.Event, interval: float):
    # # https://stackoverflow.com/questions/11219213/read-specific-windows-event-log-event
    server = 'localhost'  # name of the target computer to get event logs
    log_type = 'Microsoft-Windows'  # 'Application' / 'System'
    handle = win32evtlog.OpenEventLog(server, log_type)
    flags = win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
    # total = win32evtlog.GetNumberOfEventLogRecords(hand)

    while not kill.is_set():
        events = win32evtlog.ReadEventLog(handle, flags, 0)
        # events_list = [event for event in events if event.EventID == "27035"]
        # events_list = [event for event in events if event.EventType in (2, 4)]
        for event in events:
            print(event.EventID, event.SourceName, event.EventCategory, event.EventType, event.StringInserts)

        kill.wait(interval)

    win32evtlog.CloseEventLog(handle)
