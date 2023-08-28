#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys

assert sys.platform == "linux"

import subprocess
import threading

import math
from typing import Optional, List, Union, cast, Tuple

import Xlib.display
import Xlib.X
import Xlib.protocol
import Xlib.xobject
from Xlib.ext import randr

from ._main import BaseMonitor, _pointInBox, _getRelativePosition, \
                   DisplayMode, ScreenValue, Box, Rect, Point, Size, Position, Orientation
from ewmhlib import displaysCount, getDisplaysNames, defaultDisplay, defaultRoot, defaultScreen, defaultRootWindow, \
                    getProperty, getPropertyValue, Props

# Check if randr extension is available
if not defaultRootWindow.display.has_extension('RANDR'):
    sys.stderr.write('{}: server does not have the RANDR extension\n'.format(sys.argv[0]))
    ext = defaultRootWindow.display.query_extension('RANDR')
    print(ext)
    sys.stderr.write("\n".join(defaultRootWindow.display.list_extensions()))
    if ext is None:
        sys.exit(1)

# Check if Xorg is running (this all will not work on Wayland or alike)
p = subprocess.Popen(["xset", "-q"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
p.communicate()
if p.returncode != 0:
    sys.stderr.write('{}: Xorg is not available\n'.format(sys.argv[0]))
    sys.exit(1)


def _XgetDisplays() -> List[Xlib.display.Display]:
    displays: List[Xlib.display.Display] = []
    if displaysCount > 1 or defaultDisplay.screen_count() > 1:
        for name in getDisplaysNames():
            try:
                displays.append(Xlib.display.Display(name))
            except:
                pass
    if not displays:
        displays = [defaultDisplay]
    return displays
_displays = _XgetDisplays()


def _XgetRoots():
    roots = []
    if displaysCount > 1 or defaultDisplay.screen_count() > 1:
        global _displays
        for display in _displays:
            for i in range(display.screen_count()):
                try:
                    screen = display.screen(i)
                    res = screen.root.xrandr_get_screen_resources()
                    roots.append([display, screen, screen.root, res])
                except:
                    pass
    if not roots:
        res = defaultRoot.xrandr_get_screen_resources()
        roots.append([defaultDisplay, defaultScreen, defaultRoot, res])
    return roots
_roots = _XgetRoots()


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
    global _roots
    for rootData in _roots:
        display, screen, root, res = rootData
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
    for monName in monitors.keys():
        if monName not in arrangement.keys():
            return
    primaryPresent = False
    for monName in arrangement.keys():
        relPos = arrangement[monName]["relativePos"]
        relMon = arrangement[monName]["relativeTo"]
        if monName not in monitors.keys() or (relMon and relMon not in monitors.keys()) or \
                (not relMon and relPos != Position.PRIMARY):
            return
        elif relPos == Position.PRIMARY:
            primaryPresent = True
    if not primaryPresent:
        return

    newArrangement: dict[str, dict[str, Union[int, bool]]] = {}
    newPos: dict[str, dict[str, int]] = {}
    xOffset = yOffset = 0
    for monName in arrangement.keys():
        arrInfo = arrangement[monName]

        targetMonInfo = monitors[monName]["monitor"]
        relativePos: Position = arrInfo["relativePos"]
        relativeTo: str = arrInfo["relativeTo"]

        targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                     "position": Point(targetMonInfo.x, targetMonInfo.y),
                     "size": Size(targetMonInfo.width_in_pixels, targetMonInfo.height_in_pixels)}

        if relativePos == Position.PRIMARY:
            x, y = 0, 0

        else:
            relMonInfo = monitors[relativeTo]["monitor"]
            if relativeTo in newPos.keys():
                relX, relY = newPos[relativeTo]["x"], newPos[relativeTo]["y"]
            else:
                relX, relY = relMonInfo.x, relMonInfo.y
            relMon = {"position": Point(relX, relY),
                      "size": Size(relMonInfo.width_in_pixels, relMonInfo.height_in_pixels)}

            x, y = _getRelativePosition(targetMon, relMon)
            if x < 0:
                xOffset += abs(x)
            if y < 0:
                yOffset += abs(y)
        newPos[monName] = {"x": x, "y": y}
        w, h = targetMonInfo.width_in_pixels, targetMonInfo.height_in_pixels

        newArrangement[monName] = {
            "setPrimary": relativePos == Position.PRIMARY,
            "x": x,
            "y": y,
            "w": w,
            "h": h
        }

    if newArrangement:
        cmd = _buildCommand(newArrangement, xOffset, yOffset)
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
        except:
            pass


def _getMousePos() -> Point:
    """
    Get the current coordinates (x, y) of the mouse pointer on given monitor, in pixels

    :return: Point struct
    """
    mp = defaultRootWindow.root.query_pointer()
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

    def setPosition(self, relativePos: Union[int, Position], relativeTo: Optional[str]):
        # https://askubuntu.com/questions/1193940/setting-monitor-scaling-to-200-with-xrandr
        _setPosition(cast(Position, relativePos), relativeTo, self.name)

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
                try:
                    ret = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
                    if ret and hasattr(ret, "returncode") and ret.returncode != 0:
                        cmd = "xrandr --output %s --scale %sx%s" % (self.name, scaleX, scaleY)
                        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
                except:
                    pass

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
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
            except:
                pass

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
        err, ret = subprocess.getstatusoutput(cmd)
        if err == 0 and ret:
            try:
                value = int(float(ret)) * 100
            except:
                pass
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
                try:
                    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
                except:
                    pass

    @property
    def contrast(self) -> Optional[int]:
        value = None
        cmd = "xrandr --verbose | grep %s -A 10 | grep Gamma | grep -o '[0-9].*'" % self.name
        err, ret = subprocess.getstatusoutput(cmd)
        if err == 0 and ret:
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
                try:
                    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
                except:
                    pass

    @property
    def mode(self) -> Optional[DisplayMode]:
        value = None
        cmd = "xrandr -q | grep %s -A 50 | grep '* \\|*+'" % self.name
        err, ret = subprocess.getstatusoutput(cmd)
        if err == 0 and ret:
            try:
                res = ret.split(" ")
                lines = list(filter(None, res))
                w, h = lines[0].split("x")
                r = float(lines[1].replace("+", "").replace("*", ""))
                value = DisplayMode(int(w), int(h), r)
            except:
                pass
        return value

    def setMode(self, mode: Optional[DisplayMode]):
        # https://stackoverflow.com/questions/12706631/x11-change-resolution-and-make-window-fullscreen
        # Xlib.ext.randr.set_screen_size(defaultRootWindow.root, mode.width, mode.height, 0, 0)
        # Xlib.ext.randr.set_screen_config(defaultRootWindow.root, size_id, 0, 0, round(mode.frequency), 0)
        # Xlib.ext.randr.change_output_property()
        if mode is not None:
            cmd = "xrandr --output %s --mode %sx%s -r %s" % (self.name, mode.width, mode.height, round(mode.frequency, 2))
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
            except:
                pass

    @property
    def defaultMode(self) -> Optional[DisplayMode]:
        value = None
        cmd = "xrandr -q | grep %s -A 5 | grep ' +\\|*+'" % self.name
        err, ret = subprocess.getstatusoutput(cmd)
        if err == 0 and ret:
            try:
                res = ret.split(" ")
                lines = list(filter(None, res))
                a, b = lines[0].split("x")
                w = int(a)
                h = int(b)
                r = float(lines[1].replace("+", "").replace("*", ""))
                value = DisplayMode(w, h, r)
            except:
                pass
        return value

    def setDefaultMode(self):
        cmd = "xrandr --output %s --auto" % self.name
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
        except:
            pass

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
        if not self.isOn:
            cmdPart = ""
            for monName in _XgetAllMonitorsNames():
                if monName != self.name:
                    cmdPart = " --right-of %s" % monName
                    break
            cmd = ("xrandr --output %s" % self.name) + cmdPart + " --auto"
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
            except:
                pass
        else:
            cmd = "xset -q | grep ' Monitor is ' | awk '{ print$4 }'"
            try:
                err, ret = subprocess.getstatusoutput(cmd)
                if err == 0 and ret == "Standby":
                    cmd = "xset dpms force on"
                    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
            except:
                pass

    def turnOff(self):
        if self.isOn:
            cmd = "xrandr --output %s --off" % self.name
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
            except:
                pass

    def suspend(self):
        # xrandr has no standby option. xset doesn't allow to target just one output (it works at display level)
        cmd = "xset dpms force standby"
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
        except:
            pass

    @property
    def isOn(self) -> bool:
        # https://stackoverflow.com/questions/3433203/how-to-determine-if-lcd-monitor-is-turned-on-from-linux-command-line
        cmd = "xrandr --listactivemonitors"
        try:
            err, ret = subprocess.getstatusoutput(cmd)
            if err == 0:
                return self.name in ret
        except:
            pass
        return False

    def attach(self):
        # This produces the same effect, but requires to keep track of last mode used
        if self._crtc:
            crtcCode: int = self._crtc["crtc"]
            crtcInfo: Xlib.ext.randr.GetCrtcInfo = self._crtc["crtc_info"]
            randr.set_crtc_config(self.display, crtcCode, Xlib.X.CurrentTime, crtcInfo.x, crtcInfo.y, crtcInfo.mode, crtcInfo.rotation, crtcInfo.outputs)
            self._crtc = {}

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


def _getPrimaryName():
    for monitorData in _XgetAllMonitors():
        display, root, monitor, monName = monitorData
        if monitor.primary == 1:
            return monName
    return None


def _setPrimary(name: str):
    if name and name != _getPrimaryName():
        cmd = "xrandr --output %s --primary" % name
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
        except:
            pass


def _getPosition(name):
    pos: Optional[Point] = None
    for monitorData in _XgetAllMonitors(name):
        display, root, monitor, monName = monitorData
        pos = Point(monitor.x, monitor.y)
    return pos


def _setPosition(relativePos: Position, relativeTo: Optional[str], name: str):
    if relativePos == Position.PRIMARY:
        _setPrimary(name)

    else:
        monitors = _XgetAllMonitorsDict()
        arrangement: dict[str, dict[str, Union[int, bool]]] = {}
        xOffset = yOffset = 0
        if name in monitors.keys() and relativeTo in monitors.keys():
            newPos: dict[str, dict[str, int]] = {}
            for monitor in monitors.keys():
                if name == monitor:
                    targetMonInfo = monitors[monitor]["monitor"]
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
                    w, h = targetMonInfo.width_in_pixels, targetMonInfo.height_in_pixels
                    setPrimary = targetMonInfo.primary == 1

                    newPos[monitor] = {"x": x, "y": y, "w": w, "h": h}

                else:
                    monInfo = monitors[monitor]["monitor"]
                    x, y = monInfo.x, monInfo.y
                    w, h = monInfo.width_in_pixels, monInfo.height_in_pixels
                    setPrimary = monInfo.primary == 1
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
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, timeout=1)
            except:
                pass


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
    err, ret = subprocess.getstatusoutput(cmd)
    if err == 0 and ret:
        try:
            res = ret.split(" ")
            lines = list(filter(None, res))
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
    global _roots
    for rootData in _roots:
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
    global _roots
    for rootData in _roots:
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
    global _roots
    for rootData in _roots:
        display, screen, root, res = rootData
        for monitor in randr.get_monitors(root).monitors:
            monitors[display.get_atom_name(monitor.name)] = {"display": display, "root": root, "monitor": monitor}
    return monitors


def _XgetAllMonitorsNames():
    monNames = []
    global _roots
    for rootData in _roots:
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
    return None


def _eventLoop(kill: threading.Event, interval: float):

    randr.select_input(defaultRootWindow.root,
                       randr.RRScreenChangeNotifyMask
                       | randr.RRCrtcChangeNotifyMask
                       | randr.RROutputChangeNotifyMask
                       | randr.RROutputPropertyNotifyMask
    )

    while not kill.is_set():

        count = defaultRootWindow.display.pending_events()
        while count > 0 and not kill.is_set():

            e = defaultRootWindow.display.next_event()

            if e.__class__.__name__ == randr.ScreenChangeNotify.__name__:
                print('Screen change')
                print(e._data)

            # check if we're getting one of the RandR event types with subcodes
            elif e.type == defaultRootWindow.display.extension_event.CrtcChangeNotify[0]:
                # yes, check the subcodes

                # CRTC information has changed
                if (e.type, e.sub_code) == defaultRootWindow.display.extension_event.CrtcChangeNotify:
                    print('CRTC change')
                    # e = randr.CrtcChangeNotify(display=display.display, binarydata = e._binary)
                    print(e._data)

                # Output information has changed
                elif (e.type, e.sub_code) == defaultRootWindow.display.extension_event.OutputChangeNotify:
                    print('Output change')
                    # e = randr.OutputChangeNotify(display=display.display, binarydata = e._binary)
                    print(e._data)

                # Output property information has changed
                elif (e.type, e.sub_code) == defaultRootWindow.display.extension_event.OutputPropertyNotify:
                    print('Output property change')
                    # e = randr.OutputPropertyNotify(display=display.display, binarydata = e._binary)
                    print(e._data)

                else:
                    print("Unrecognised subcode", e.sub_code)

            count -= 1
        kill.wait(interval)
