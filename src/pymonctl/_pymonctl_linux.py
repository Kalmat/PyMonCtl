#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
assert sys.platform == "linux"

import subprocess
import threading

import math
from typing import Optional, List, Union, Tuple

import Xlib.display
import Xlib.X
import Xlib.protocol
import Xlib.xobject
from Xlib.ext import randr

from ._main import BaseMonitor, _pointInBox, _getRelativePosition, \
                   DisplayMode, ScreenValue, Box, Rect, Point, Size, Position, Orientation
from ewmhlib import defaultEwmhRoot, getProperty, getPropertyValue, getRoots, getRootsInfo, Props


def _getAllMonitors() -> list[LinuxMonitor]:
    monitors = []
    outputs = _XgetAllOutputs()
    for outputData in outputs:
        display, screen, root, res, output, outputInfo = outputData
        if outputInfo.crtc:
            monitors.append(LinuxMonitor(output))
    return monitors


def _getAllMonitorsDict() -> dict[str, ScreenValue]:
    # https://stackoverflow.com/questions/8705814/get-display-count-and-resolution-for-each-display-in-python-without-xrandr
    # https://www.x.org/releases/X11R7.7/doc/libX11/libX11/libX11.html#Obtaining_Information_about_the_Display_Image_Formats_or_Screens
    # https://github.com/alexer/python-xlib/blob/master/examples/xrandr.py
    result: dict[str, ScreenValue] = {}

    outputs = _XgetAllOutputs()
    for monitorData in _XgetAllMonitors():
        display, root, monitor, monitorName = monitorData

        for outputData in outputs:
            display, screen, root, res, output, outputInfo = outputData

            if outputInfo.name == monitorName and outputInfo.crtc:
                crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, res.config_timestamp)
                is_primary = monitor.primary == 1
                x, y, w, h = monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels
                # https://askubuntu.com/questions/1124149/how-to-get-taskbar-size-and-position-with-python
                wa: List[int] = getPropertyValue(getProperty(window=root, prop=Props.Root.WORKAREA, display=display), display=display)
                wx, wy, wr, wb = wa[0], wa[1], wa[2], wa[3]
                dpiX, dpiY = round((w * 25.4) / (monitor.width_in_millimeters or 1)), round((h * 25.4) / (monitor.height_in_millimeters or 1))
                scaleX, scaleY = _scale(monitorName) or (0.0, 0.0)
                rot = int(math.log(crtcInfo.rotation, 2))
                freq = 0.0
                for mode in res.modes:
                    if crtcInfo.mode == mode.id:
                        freq = round(mode.dot_clock / ((mode.h_total * mode.v_total) or 1), 2)
                        break
                depth = screen.root_depth

                result[outputInfo.name] = {
                    "system_name": outputInfo.name,
                    'id': output,
                    'is_primary': is_primary,
                    'position': Point(x, y),
                    'size': Size(w, h),
                    'workarea': Rect(wx, wy, wr, wb),
                    'scale': (scaleX, scaleY),
                    'dpi': (dpiX, dpiY),
                    'orientation': rot,
                    'frequency': freq,
                    'colordepth': depth
                }
                break
    return result


def _getMonitorsCount() -> int:
    count = 0
    for root in getRoots():
        count += len(randr.get_monitors(root).monitors)
    return count


def _findMonitor(x: int, y: int) -> List[LinuxMonitor]:
    monitors = []
    for monitor in _getAllMonitors():
        if monitor.position is not None and monitor.size is not None:
            if _pointInBox(x, y, monitor.position.x, monitor.position.y, monitor.size.width, monitor.size.height):
                monitors.append(monitor)
    return monitors


def _getPrimary() -> LinuxMonitor:
    return LinuxMonitor()


def _arrangeMonitors(arrangement: dict[str, dict[str, Union[str, int, Position, Point, Size]]]):

    monitors = _XgetAllMonitorsDict()
    setAsPrimary = ""
    primaryPresent = False
    for monName in arrangement.keys():
        relPos = arrangement[monName]["relativePos"]
        relMon = arrangement[monName].get("relativeTo", "")
        if (monName not in monitors.keys() or
                ((isinstance(relPos, Position) or isinstance(relPos, int)) and
                 ((relMon and relMon not in monitors.keys()) or (not relMon and relPos != Position.PRIMARY)))):
            return
        elif relPos == Position.PRIMARY:
            setAsPrimary = monName
            primaryPresent = True
    if not primaryPresent:
        return

    newArrangement: dict[str, dict[str, Union[int, bool]]] = {}
    newPos: dict[str, dict[str, int]] = {}
    xOffset = yOffset = 0

    for monName in arrangement.keys():

        arrInfo = arrangement[monName]
        relativePos: Union[Position, Point] = arrInfo["relativePos"]
        targetMonInfo = monitors[monName]["monitor"]

        if monName == setAsPrimary:
            setPrimary = True
            x, y = 0, 0

        else:

            setPrimary = False

            if isinstance(relativePos, Position) or isinstance(relativePos, int):

                relativeTo: str = arrInfo["relativeTo"]

                targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                             "position": Point(targetMonInfo.x, targetMonInfo.y),
                             "size": Size(targetMonInfo.width_in_pixels, targetMonInfo.height_in_pixels)}

                relMonInfo = monitors[relativeTo]["monitor"]
                if relativeTo in newPos.keys():
                    relX, relY = newPos[relativeTo]["x"], newPos[relativeTo]["y"]
                else:
                    relX, relY = relMonInfo.x, relMonInfo.y
                relMon = {"position": Point(relX, relY),
                          "size": Size(relMonInfo.width_in_pixels, relMonInfo.height_in_pixels)}

                x, y = _getRelativePosition(targetMon, relMon)

            else:
                x, y = relativePos

            if x < 0:
                xOffset += abs(x)
            if y < 0:
                yOffset += abs(y)
        newPos[monName] = {"x": x, "y": y}
        w, h = targetMonInfo.width_in_pixels, targetMonInfo.height_in_pixels

        newArrangement[monName] = {
            "setPrimary": setPrimary,
            "x": x,
            "y": y,
            "w": w,
            "h": h
        }

    if newArrangement:
        cmd = _buildCommand(newArrangement, xOffset, yOffset)
        _ = _runProc(cmd)


def _getMousePos() -> Point:
    """
    Get the current coordinates (x, y) of the mouse pointer on given monitor, in pixels

    :return: Point struct
    """
    mp = defaultEwmhRoot.root.query_pointer()
    return Point(mp.root_x, mp.root_y)


class LinuxMonitor(BaseMonitor):

    def __init__(self, handle: Optional[int] = None):
        """
        Class to access all methods and functions to get info and manage monitors plugged to the system.

        This class is not meant to be directly instantiated. Instead, use convenience functions like getAllMonitors(),
        getPrimary() or findMonitor(x, y).

        It can raise ValueError exception in case provided handle is not valid
        """
        monitorData = _XgetMonitorData(handle)
        if monitorData is not None:
            self.display, self.screen, self.root, self.resources, self.handle, self.name = monitorData
        else:
            raise ValueError
        self._crtc: dict[str, Union[int, Xlib.ext.randr.GetCrtcInfo]] = {}

    @property
    def size(self) -> Optional[Size]:
        size: Optional[Size] = None
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            size = Size(monitor.width_in_pixels, monitor.height_in_pixels)
        return size

    @property
    def workarea(self) -> Optional[Rect]:
        res: Optional[Rect] = None
        # https://askubuntu.com/questions/1124149/how-to-get-taskbar-size-and-position-with-python
        wa: List[int] = getPropertyValue(
            getProperty(window=self.root, prop=Props.Root.WORKAREA, display=self.display), display=self.display)
        if wa:
            wx, wy, wr, wb = wa[0], wa[1], wa[2], wa[3]
            res = Rect(wx, wy, wr, wb)
        return res

    @property
    def position(self) -> Optional[Point]:
        pos: Optional[Point] = None
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            pos = Point(monitor.x, monitor.y)
        return pos

    def setPosition(self, relativePos: Union[int, Position, Point, Tuple[int, int]], relativeTo: Optional[str]):
        # https://askubuntu.com/questions/1193940/setting-monitor-scaling-to-200-with-xrandr
        _setPosition(relativePos, relativeTo, self.name)

    @property
    def box(self) -> Optional[Box]:
        box: Optional[Box] = None
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            box = Box(monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels)
            break
        return box

    @property
    def rect(self) -> Optional[Rect]:
        rect: Optional[Rect] = None
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            rect = Rect(monitor.x, monitor.y, monitor.x + monitor.width_in_pixels, monitor.y + monitor.height_in_pixels)
            break
        return rect

    @property
    def scale(self) -> Optional[Tuple[float, float]]:
        return _scale(self.name)

    def setScale(self, scale: Optional[Tuple[float, float]]):
        if scale is not None:
            # https://askubuntu.com/questions/1193940/setting-monitor-scaling-to-200-with-xrandr
            scaleX, scaleY = round(100 / scale[0], 1), round(100 / scale[1], 1)
            if 0 < scaleX <= 1 and 0 < scaleY <= 1:
                cmd = "xrandr --output %s --scale %sx%s --filter nearest" % (self.name, scaleX, scaleY)
                ret = _runProc(cmd)
                if not ret:
                    cmd = "xrandr --output %s --scale %sx%s" % (self.name, scaleX, scaleY)
                    _ = _runProc(cmd)

    @property
    def dpi(self) -> Optional[Tuple[float, float]]:
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            x, y, w, h = monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels
            dpiX, dpiY = round((w * 25.4) / monitor.width_in_millimeters), round((h * 25.4) / monitor.height_in_millimeters)
            return dpiX, dpiY
        return None

    @property
    def orientation(self) -> Optional[Union[int, Orientation]]:
        for outputData in _XgetAllOutputs(self.name):
            display, screen, root, res, output, outputInfo = outputData
            if outputInfo.crtc:
                crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, res.config_timestamp)
                rot = int(math.log(crtcInfo.rotation, 2))
                return rot
        return None

    def setOrientation(self, orientation: Optional[Union[int, Orientation]]):
        if orientation in (Orientation.NORMAL, Orientation.INVERTED, Orientation.LEFT, Orientation.RIGHT):
            # outputs = _XgetAllOutputs(self.name)
            # for outputData in outputs:
            #     display, screen, root, res, output, outputInfo = outputData
            #     crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, res.config_timestamp)
            #     if crtcInfo and crtcInfo.mode:
            #         randr.set_crtc_config(display, outputInfo.crtc, Xlib.X.CurrentTime, crtcInfo.x, crtcInfo.y,
            #                               crtcInfo.mode, (orientation or 1) ** 2, crtcInfo.outputs)

            if orientation == Orientation.RIGHT:
                direction = "right"
            elif orientation == Orientation.INVERTED:
                direction = "inverted"
            elif orientation == Orientation.LEFT:
                direction = "left"
            else:
                direction = "normal"
            cmd = "xrandr --output %s --rotate %s" % (self.name, direction)
            _ = _runProc(cmd)

    @property
    def frequency(self) -> Optional[float]:
        outputs = _XgetAllOutputs(self.name)
        for outputData in outputs:
            display, screen, root, res, output, outputInfo = outputData
            crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, res.config_timestamp)
            for mode in res.modes:
                if crtcInfo.mode == mode.id:
                    return float(round(mode.dot_clock / ((mode.h_total * mode.v_total) or 1), 2))
        return None
    refreshRate = frequency

    @property
    def colordepth(self) -> int:
        return int(self.screen.root_depth)

    @property
    def brightness(self) -> Optional[int]:
        # https://manerosss.wordpress.com/2017/05/16/brightness-linux-xrandr/
        value = None
        cmd = "xrandr --verbose | grep %s -A 10 | grep Brightness | grep -o '[0-9].*'" % self.name
        ret = _runProc(cmd)
        if ret:
            value = int(float(ret)) * 100
        return value

        # Pointers to misc solutions
        #     # https://stackoverflow.com/questions/16402672/control-screen-with-python
        #     if int(brightness) > 15:
        #         raise TypeError("Need int 0 < and > 15")
        #     elif int(brightness) < 0:
        #         raise TypeError("Need int 0 < and > 15")
        #     with open("/sys/devices/pci0000:00/0000:00:02.0/backlight/acpi_video0/brightness", "w") as bright:
        #         bright.write(str(brightness))
        #         bright.close()
        #
        #     # https://github.com/arjun024/turn-off-screen/blob/master/platform-specific/turnoff_win8.1.py
        #     os.system("xset dpms force off")
        #
        #     # https://stackoverflow.com/questions/47026351/change-backlight-brightness-in-linux-with-python
        #     os.system('gdbus call --session '
        #               '--dest org.gnome.SettingsDaemon.Power '
        #               '--object-path /org/gnome/SettingsDaemon/Power '
        #               '--method org.freedesktop.DBus.Properties.Set org.gnome.SettingsDaemon.Power.Screen '
        #               'Brightness "<int32 %s>"' % str(brightness))
        #     os.system('gdbus call --session '
        #               '--dest org.gnome.SettingsDaemon.Power '
        #               '--object-path /org/gnome/SettingsDaemon/Power '
        #               '--method org.freedesktop.DBus.Properties.Get org.gnome.SettingsDaemon.Power.Screen '
        #               'Brightness')

    def setBrightness(self, brightness: Optional[int]):
        if brightness is not None:
            value = brightness / 100
            if 0 <= value <= 1:
                cmd = "xrandr --output %s --brightness %s" % (self.name, str(value))
                _ = _runProc(cmd)

    @property
    def contrast(self) -> Optional[int]:
        value = None
        cmd = "xrandr --verbose | grep %s -A 10 | grep Gamma | grep -o '[0-9].*'" % self.name
        ret = _runProc(cmd)
        if ret:
            r, g, b = ret.split(":")
            value = int(((1 / (float(r) or 1)) + (1 / (float(g) or 1)) + (1 / (float(b) or 1))) / 3) * 100
        return value

    def setContrast(self, contrast: Optional[int]):
        if contrast is not None:
            value = contrast / 100
            if 0 <= value <= 1:
                rgb = str(round(value, 1))
                gamma = rgb + ":" + rgb + ":" + rgb
                cmd = "xrandr --output %s --gamma %s" % (self.name, gamma)
                _ = _runProc(cmd)

    @property
    def mode(self) -> Optional[DisplayMode]:
        for crtcData in _XgetAllCrtcs(self.name):
            display, screen, root, res, output, outputInfo, crtc, crtcInfo = crtcData
            if self.handle == output:
                if outputInfo.crtc == crtc:
                    print(crtcInfo)
                    mode = crtcInfo.mode
                    for resMode in res.modes:
                        if resMode.id == mode:
                            retMode = DisplayMode(resMode.width, resMode.height,
                                                round(resMode.dot_clock / ((resMode.h_total * resMode.v_total) or 1), 2))
                            return retMode
        return None

    def setMode(self, mode: Optional[DisplayMode]):
        # https://stackoverflow.com/questions/12706631/x11-change-resolution-and-make-window-fullscreen
        # Xlib.ext.randr.set_screen_size(defaultEwmhRoot.root, mode.width, mode.height, 0, 0)
        # Xlib.ext.randr.set_screen_config(defaultEwmhRoot.root, size_id, 0, 0, round(mode.frequency), 0)
        # Xlib.ext.randr.change_output_property()
        if mode is not None:
            cmd = "xrandr --output %s --mode %sx%s -r %s" % (self.name, mode.width, mode.height, round(mode.frequency, 2))
            _ = _runProc(cmd)

    @property
    def defaultMode(self) -> Optional[DisplayMode]:
        for outputData in _XgetAllOutputs(self.name):
            display, screen, root, res, output, outputInfo = outputData
            if self.handle == output:
                for outMode in outputInfo.modes:
                    for resMode in res.modes:
                        if outMode == resMode.id:
                            return DisplayMode(resMode.width, resMode.height,
                                               round(resMode.dot_clock / ((resMode.h_total * resMode.v_total) or 1), 2))
                break
        return None

    def setDefaultMode(self):
        cmd = "xrandr --output %s --auto" % self.name
        _ = _runProc(cmd)

    @property
    def allModes(self) -> list[DisplayMode]:
        modes: List[DisplayMode] = []
        for outputData in _XgetAllOutputs(self.name):
            display, screen, root, res, output, outputInfo = outputData
            if self.handle == output:
                for outMode in outputInfo.modes:
                    for resMode in res.modes:
                        if outMode == resMode.id:
                            modes.append(DisplayMode(resMode.width, resMode.height,
                                                     round(resMode.dot_clock / ((resMode.h_total * resMode.v_total) or 1), 2)))
                break
        return modes

    @property
    def isPrimary(self) -> bool:
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            return bool(monitor.primary == 1)
        return False

    def setPrimary(self):
        _setPrimary(self.name)

    def turnOn(self):
        cmd = ""
        if self.isSuspended:
            cmd = "xset dpms force on"
        elif not self.isOn:
            cmdPart = ""
            relativeTo = self.name
            for monName in _XgetAllMonitorsNames():
                if monName != self.name:
                    cmdPart += " --output %s --left-of %s" % (monName, relativeTo)
                    relativeTo = monName
            cmd = str("xrandr --output %s --auto" % self.name) + cmdPart
        if cmd:
            _ = _runProc(cmd)


    def turnOff(self):
        if self.isOn:
            cmd = "xrandr --output %s --off" % self.name
            _ = _runProc(cmd)

    @property
    def isOn(self) -> Optional[bool]:
        # https://stackoverflow.com/questions/3433203/how-to-determine-if-lcd-monitor-is-turned-on-from-linux-command-line
        cmd = "xrandr --listactivemonitors"
        res: Optional[bool] = None
        ret = _runProc(cmd)
        if ret:
            res = self.name in ret
        isSuspended = self.isSuspended
        return (res and not isSuspended) if isSuspended is not None else res

    def suspend(self):
        # xrandr has no standby option. xset doesn't allow to target just one output (it works at display level)
        cmd = "xset dpms force standby"
        _ = _runProc(cmd)

    @property
    def isSuspended(self) -> Optional[bool]:
        cmd = "xset -q | grep ' Monitor is '"
        ret = _runProc(cmd)
        if ret:
            return bool("Standby" in ret)
        return None

    def attach(self):
        # This produces the same effect, but requires to keep track of last mode used
        if self._crtc:
            crtc: int = self._crtc["crtc"]
            crtcInfo: Xlib.ext.randr.GetCrtcInfo = self._crtc["crtc_info"]
            randr.set_crtc_config(self.display, crtc, Xlib.X.CurrentTime, crtcInfo.x, crtcInfo.y, crtcInfo.mode, crtcInfo.rotation, crtcInfo.outputs)
            self._crtc = {}
            cmdPart = ""
            relativeTo = self.name
            for monName in _XgetAllMonitorsNames():
                if monName != self.name:
                    cmdPart += " --output %s --left-of %s" % (monName, relativeTo)
                    relativeTo = monName
            cmd = str("xrandr --output %s --auto" % self.name) + cmdPart
            _ = _runProc(cmd)


    def detach(self, permanent: bool = False):
        # This produces the same effect, but requires to keep track of last mode used
        outputs = _XgetAllOutputs(self.name)
        for outputData in outputs:
            display, screen, root, res, output, outputInfo = outputData
            if outputInfo.crtc:
                crtcInfo: Xlib.ext.randr.GetCrtcInfo = randr.get_crtc_info(display, outputInfo.crtc, Xlib.X.CurrentTime)
                randr.set_crtc_config(display, outputInfo.crtc, Xlib.X.CurrentTime, crtcInfo.x, crtcInfo.y, 0, crtcInfo.rotation, [])
                self._crtc = {"crtc": outputInfo.crtc, "crtc_info": crtcInfo}

    @property
    def isAttached(self) -> bool:
        outputs = _XgetAllOutputs(self.name)
        for outputData in outputs:
            display, screen, root, res, output, outputInfo = outputData
            if outputInfo.crtc:
                crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, Xlib.X.CurrentTime)
                if crtcInfo.mode != 0:
                    return True
                break
        return False


def _setPrimary(name: str):
    cmd = "xrandr --output %s --primary" % name
    _ = _runProc(cmd)


def _getPosition(name):
    pos: Optional[Point] = None
    for monitorData in _XgetAllMonitors(name):
        display, root, monitor, monName = monitorData
        pos = Point(monitor.x, monitor.y)
    return pos


def _setPosition(relativePos: Union[int, Position, Point, Tuple[int, int]], relativeTo: Optional[str], name: str):
    if relativePos == Position.PRIMARY:
        _setPrimary(name)

    else:
        monitors = _XgetAllMonitorsDict()
        monitorsKeys = list(monitors.keys())
        arrangement: dict[str, dict[str, Union[int, bool]]] = {}
        xOffset = yOffset = 0

        if (name not in monitorsKeys or
                ((isinstance(relativePos, Position) or isinstance(relativePos, int)) and
                 (not relativeTo or (relativeTo and relativeTo not in monitors.keys())))):
            return

        newPos: dict[str, dict[str, int]] = {}
        for monitor in monitorsKeys:

            targetMonInfo = monitors[monitor]["monitor"]
            w, h = targetMonInfo.width_in_pixels, targetMonInfo.height_in_pixels
            setPrimary = targetMonInfo.primary == 1

            if name == monitor:

                if isinstance(relativePos, Position) or isinstance(relativePos, int):
                    targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                                 "position": Point(targetMonInfo.x, targetMonInfo.y),
                                 "size": Size(targetMonInfo.width_in_pixels, targetMonInfo.height_in_pixels)}

                    relMonInfo = monitors[relativeTo]["monitor"]
                    if relativeTo in newPos.keys():
                        x, y = newPos[relativeTo]["x"], newPos[relativeTo]["y"]
                    else:
                        x, y = relMonInfo.x, relMonInfo.y
                    relMon = {"position": Point(x, y),
                              "size": Size(relMonInfo.width_in_pixels, relMonInfo.height_in_pixels)}

                    x, y = _getRelativePosition(targetMon, relMon)

                else:
                    x, y = relativePos

                newPos[monitor] = {"x": x, "y": y, "w": w, "h": h}

            else:
                x, y = targetMonInfo.x, targetMonInfo.y
                setPrimary = targetMonInfo.primary == 1
            if x < 0:
                xOffset += abs(x)
            if y < 0:
                yOffset += abs(y)

            arrangement[monitor] = {
                "setPrimary": setPrimary,
                "x": x,
                "y": y,
                "w": w,
                "h": h
            }
        if arrangement:
            cmd = _buildCommand(arrangement, xOffset, yOffset)
            _ = _runProc(cmd)


def _buildCommand(arrangement: dict[str, dict[str, Union[int, bool]]], xOffset: int, yOffset: int):
    cmd = "xrandr"
    for monName in arrangement.keys():
        arrInfo = arrangement[monName]
        cmd += " --output %s" % monName
        # xrandr won't accept negative values!!!!
        # https://superuser.com/questions/485120/how-do-i-align-the-bottom-edges-of-two-monitors-with-xrandr
        cmd += " --pos %sx%s" % (str(int(arrInfo["x"]) + xOffset), str(int(arrInfo["y"]) + yOffset))
        cmd += " --mode %sx%s" % (arrInfo["w"], arrInfo["h"])
        if arrInfo["setPrimary"]:
            cmd += " --primary"
    return cmd


def _scale(name: str = "") -> Optional[Tuple[float, float]]:
    value = None
    cmd = "xrandr -q | grep %s -A 5 | grep ' +\\|*+'" % name
    ret = _runProc(cmd)
    if ret:
        try:
            res = ret.split(" ")
            lines: List[str] = list(filter(None, res))
            a, b = lines[0].split("x")
            w = int(a)
            h = int(b)
            r = float(lines[1].replace("+", "").replace("*", ""))
            value = DisplayMode(w, h, r)
        except:
            pass
    if value:
        for monitorData in _XgetAllMonitors(name):
            display, root, monitor, monName = monitorData
            w, h = monitor.width_in_pixels, monitor.height_in_pixels
            wm, hm = monitor.width_in_millimeters, monitor.height_in_millimeters
            if wm and hm:
                wDef, hDef = value.width, value.height
                dpiXDef, dpiYDef = round((wDef * 25.4) / wm), round((hDef * 25.4) / hm)
                dpiX, dpiY = round((w * 25.4) / wm), round((h * 25.4) / hm)
                if dpiX and dpiY and dpiXDef and dpiYDef:
                    scaleX, scaleY = (100 / (dpiX / dpiXDef), 100 / (dpiY / dpiYDef))
                    return scaleX, scaleY
    return None


def _XgetAllOutputs(name: str = ""):
    outputs = []
    for rootData in getRootsInfo(forceUpdate=True):
        display, screen, root, res = rootData
        if res:
            for output in res.outputs:
                try:
                    outputInfo = randr.get_output_info(display, output, res.config_timestamp)
                    if not name or (name and name == outputInfo.name):
                        outputs.append([display, screen, root, res, output, outputInfo])
                except:
                    pass
    return outputs


def _XgetAllCrtcs(name: str = ""):
    crtcs = []
    outputs = _XgetAllOutputs(name)
    for outputData in outputs:
        display, screen, root, res, output, outputInfo = outputData
        if not name or (name and name == outputInfo.name):
            for crtc in outputInfo.crtcs:
                try:
                    crtcInfo = randr.get_crtc_info(display, crtc, res.config_timestamp)
                    crtcs.append([display, screen, root, res, output, outputInfo, crtc, crtcInfo])
                except:
                    pass
            if name:
                return crtcs
    return crtcs


def _XgetAllMonitors(name: str = ""):
    monitors = []
    for rootData in getRootsInfo():
        display, screen, root, res = rootData
        for monitor in randr.get_monitors(root).monitors:
            monName = display.get_atom_name(monitor.name)
            if not name or (name and name == monName):
                monitors.append([display, root, monitor, monName])
                if name:
                    return monitors
    return monitors


def _XgetAllMonitorsDict():
    monitors = {}
    for rootData in getRootsInfo():
        display, screen, root, res = rootData
        for monitor in randr.get_monitors(root).monitors:
            monitors[display.get_atom_name(monitor.name)] = {"display": display, "root": root, "monitor": monitor}
    return monitors


def _XgetAllMonitorsNames():
    monNames = []
    for rootData in getRootsInfo():
        display, screen, root, res = rootData
        for monitor in randr.get_monitors(root).monitors:
            monNames.append(display.get_atom_name(monitor.name))
    return monNames


def _XgetPrimary():
    outputs = _XgetAllOutputs()
    for monitorData in _XgetAllMonitors():
        display, root, monitor, monName = monitorData
        if monitor.primary == 1:
            for outputData in outputs:
                display, screen, root, res, output, outputInfo = outputData
                if outputInfo.name == monName:
                    handle = output
                    return handle, monName
    return None


def _XgetMonitorData(handle: Optional[int] = None):
    outputs = _XgetAllOutputs()
    if handle:
        for outputData in outputs:
            display, screen, root, res, output, outputInfo = outputData
            if output == handle:
                return display, screen, root, res, output, outputInfo.name
    else:
        monitors = _XgetAllMonitors()
        for monitorData in monitors:
            display, root, monitor, monName = monitorData
            if monitor.primary == 1 or len(monitors) == 1:
                for outputData in outputs:
                    display, screen, root, res, output, outputInfo = outputData
                    if monName == outputInfo.name and outputInfo.crtc:
                        return display, screen, root, res, output, outputInfo.name
    for outputData in outputs:
        display, screen, root, res, output, outputInfo = outputData
        if root.id == defaultEwmhRoot.root.id:
            return display, screen, root, res, output, outputInfo.name
    return None


def _runProc(cmd: str, timeout: int = 1):
    if timeout <= 0:
        timeout = 1
    proc = subprocess.run(cmd, text=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if proc.returncode == 0:
        return proc.stdout
    return None


def _checkEnvironment():

    # Check if randr extension is available
    if not defaultEwmhRoot.display.has_extension('RANDR'):
        sys.stderr.write('{}: server does not have the RANDR extension\n'.format(sys.argv[0]))
        ext = defaultEwmhRoot.display.query_extension('RANDR')
        print(ext)
        sys.stderr.write("\n".join(defaultEwmhRoot.display.list_extensions()))
        if ext is None:
            sys.exit(1)

    # Check if Xorg is running and xset is present (this will not work on Wayland or alike)
    cmd = "xset -q"
    ret = _runProc(cmd)
    if not ret:
        sys.stderr.write('{}: Xorg and/or xset are not available\n'.format(sys.argv[0]))
        sys.exit(1)

    # Check if xrandr is present (it will not in distributions like Arch or Manjaro)
    cmd = "xrandr -q"
    ret = _runProc(cmd)
    if not ret:
        sys.stderr.write(
            '{}: Xorg and/or xrandr are not available\n'.format(sys.argv[0]))
        sys.exit(1)
_checkEnvironment()


def _eventLoop(kill: threading.Event, interval: float):

    randr.select_input(defaultEwmhRoot.root,
                       randr.RRScreenChangeNotifyMask
                       | randr.RRCrtcChangeNotifyMask
                       | randr.RROutputChangeNotifyMask
                       | randr.RROutputPropertyNotifyMask
    )

    while not kill.is_set():

        count = defaultEwmhRoot.display.pending_events()
        while count > 0 and not kill.is_set():

            e = defaultEwmhRoot.display.next_event()

            if e.__class__.__name__ == randr.ScreenChangeNotify.__name__:
                print('Screen change')
                print(e._data)

            # check if we're getting one of the RandR event types with subcodes
            elif e.type == defaultEwmhRoot.display.extension_event.CrtcChangeNotify[0]:
                # yes, check the subcodes

                # CRTC information has changed
                if (e.type, e.sub_code) == defaultEwmhRoot.display.extension_event.CrtcChangeNotify:
                    print('CRTC change')
                    # e = randr.CrtcChangeNotify(display=display.display, binarydata = e._binary)
                    print(e._data)

                # Output information has changed
                elif (e.type, e.sub_code) == defaultEwmhRoot.display.extension_event.OutputChangeNotify:
                    print('Output change')
                    # e = randr.OutputChangeNotify(display=display.display, binarydata = e._binary)
                    print(e._data)

                # Output property information has changed
                elif (e.type, e.sub_code) == defaultEwmhRoot.display.extension_event.OutputPropertyNotify:
                    print('Output property change')
                    # e = randr.OutputPropertyNotify(display=display.display, binarydata = e._binary)
                    print(e._data)

                else:
                    print("Unrecognised subcode", e.sub_code)

            count -= 1
        kill.wait(interval)
