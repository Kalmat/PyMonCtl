#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
import threading
import time

assert sys.platform == "linux"

import math
import os
from typing import Optional, List, Union

import Xlib.display
import Xlib.X
from Xlib.ext import randr

from pymonctl import BaseMonitor, _pointInBox, _getRelativePosition
from .structs import *
from ewmhlib import Props, defaultRootWindow, getProperty, getPropertyValue


if not defaultRootWindow.display.has_extension('RANDR'):
    sys.stderr.write('{}: server does not have the RANDR extension\n'.format(sys.argv[0]))
    ext = defaultRootWindow.display.query_extension('RANDR')
    print(ext)
    sys.stderr.write("\n".join(defaultRootWindow.display.list_extensions()))
    if ext is None:
        sys.exit(1)


def _XgetDisplays() -> List[Xlib.display.Display]:
    displays: List[Xlib.display.Display] = []
    try:
        files = os.listdir("/tmp/.X11-unix")
    except:
        files = []
    for f in files:
        if f.startswith("X"):
            displays.append(Xlib.display.Display(":"+f[1:]))
    if not displays:
        displays = [Xlib.display.Display()]
    return displays
_displays = _XgetDisplays()


def _XgetRoots():
    roots = []
    global _displays
    for display in _displays:
        for i in range(display.screen_count()):
            try:
                screen = display.screen(i)
                roots.append([display, screen, screen.root])
            except:
                pass
    return roots
_roots = _XgetRoots()


def _getAllMonitors() -> list[Monitor]:
    monitors = []
    for outputData in _XgetAllOutputs():
        display, screen, root, res, output, outputInfo = outputData
        if outputInfo.crtc:
            monitors.append(Monitor(output))
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
                is_primary = monitor.primary == 1 or (monitor.x == 0 and monitor.y == 0)
                x, y, w, h = monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels
                # https://askubuntu.com/questions/1124149/how-to-get-taskbar-size-and-position-with-python
                wa: List[int] = getPropertyValue(getProperty(window=root, prop=Props.Root.WORKAREA.value, display=display), display=display)
                wx, wy, wr, wb = wa[0], wa[1], wa[2], wa[3]
                dpiX, dpiY = round((w * 25.4) / monitor.width_in_millimeters), round((h * 25.4) / monitor.height_in_millimeters)
                scaleX, scaleY = round((dpiX / 96) * 100), round((dpiY / 96) * 100)
                rot = int(math.log(crtcInfo.rotation, 2))
                freq = 0.0
                for mode in res.modes:
                    if crtcInfo.mode == mode.id:
                        freq = round(mode.dot_clock / ((mode.h_total * mode.v_total) or 1), 2)
                        break
                depth = screen.root_depth

                result[outputInfo.name] = {
                    "system_name": outputInfo.name,
                    'handle': output,
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
        display, screen, root = rootData
        count += len(randr.get_monitors(root).monitors)
    return count


def _findMonitor(x: int, y: int) -> Optional[Monitor]:
    for monitor in _getAllMonitors():
        if _pointInBox(x, y, monitor.position.x, monitor.position.y, monitor.size.width, monitor.size.height):
            return monitor
    return None


def _getPrimary() -> Monitor:
    return Monitor()


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
                (not relMon and relPos != PRIMARY):
            return
        elif relPos == PRIMARY:
            primaryPresent = True
    if not primaryPresent:
        return

    for monName in arrangement.keys():
        _setPosition(arrangement[monName]["relativePos"], arrangement[monName]["relativeTo"], monName)


def _getMousePos() -> Point:
    """
    Get the current (x, y) coordinates of the mouse pointer on screen, in pixels

    :return: Point struct
    """
    mp = defaultRootWindow.root.query_pointer()
    return Point(mp.root_x, mp.root_y)


class Monitor(BaseMonitor):

    def __init__(self, handle: Optional[int] = None):
        """
        Class to access all methods and functions to get info and manage monitors plugged to the system.

        This class is not meant to be directly instantiated. Instead, use convenience functions like getAllMonitors(),
        getPrimary() or findMonitor(x, y).
        """
        self.display, self.screen, self.root, self.resources, self.handle, self.name = _XgetMonitorData(handle)

    @property
    def size(self) -> Optional[Size]:
        res: Optional[Size] = None
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            res = Size(monitor.width_in_pixels, monitor.height_in_pixels)
        return res

    @property
    def workarea(self) -> Optional[Rect]:
        res: Optional[Rect] = None
        # https://askubuntu.com/questions/1124149/how-to-get-taskbar-size-and-position-with-python
        wa: List[int] = getPropertyValue(
            getProperty(window=self.root, prop=Props.Root.WORKAREA.value, display=self.display), display=self.display)
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

    def setPosition(self, relativePos: Position, relativeTo: Optional[str]):
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
    def scale(self) -> Tuple[float, float]:
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            x, y, w, h = monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels
            dpiX, dpiY = round((w * 25.4) / monitor.width_in_millimeters), round((h * 25.4) / monitor.height_in_millimeters)
            scaleX, scaleY = round((dpiX / 96) * 100), round((dpiY / 96) * 100)
            return scaleX, scaleY
        return 0.0, 0.0

    @scale.setter
    def scale(self, scale: float):
        # https://askubuntu.com/questions/1193940/setting-monitor-scaling-to-200-with-xrandr
        if isinstance(scale, tuple):
            scaleX, scaleY = scale
        else:
            scaleX = scaleY = scale
        cmd = " --scale %sx%s --filter nearest" % (scaleX, scaleY)
        if self.name and self.name in _XgetAllMonitorsNames():
            cmd = (" --output %s" % self.name) + cmd
        cmd = "xrandr" + cmd
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
        except:
            pass

    @property
    def dpi(self) -> Tuple[float, float]:
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            x, y, w, h = monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels
            dpiX, dpiY = round((w * 25.4) / monitor.width_in_millimeters), round((h * 25.4) / monitor.height_in_millimeters)
            return dpiX, dpiY
        return 0.0, 0.0

    @property
    def orientation(self) -> Optional[Union[int, Orientation]]:
        for outputData in _XgetAllOutputs(self.name):
            display, screen, root, res, output, outputInfo = outputData
            if outputInfo.crtc:
                crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, res.config_timestamp)
                rot = int(math.log(crtcInfo.rotation, 2))
                return rot
        return None

    @orientation.setter
    def orientation(self, orientation: Orientation):
        if orientation in (NORMAL, INVERTED, LEFT, RIGHT):
            outputs = _XgetAllOutputs(self.name)
            for outputData in outputs:
                display, screen, root, res, output, outputInfo = outputData
                crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, Xlib.X.CurrentTime)
                if crtcInfo and crtcInfo.mode:
                    randr.set_crtc_config(display, outputInfo.crtc, Xlib.X.CurrentTime, crtcInfo.x, crtcInfo.y,
                                          crtcInfo.mode, (orientation or 1) ** 2, crtcInfo.outputs)

            # if orientation == RIGHT:
            #     direction = "right"
            # elif orientation == INVERTED:
            #     direction = "inverted"
            # elif orientation == LEFT:
            #     direction = "left"
            # else:
            #     direction = "normal"
            # cmd = " -o %s" % direction
            # if name and name in __getMonitorsNames():
            #     cmd = (" --output %s" % name) + cmd
            # cmd = "xrandr" + cmd
            # try:
            #     subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
            # except:
            #     pass

    @property
    def frequency(self) -> Optional[float]:
        outputs = _XgetAllOutputs(self.name)
        for outputData in outputs:
            display, screen, root, res, output, outputInfo = outputData
            crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, Xlib.X.CurrentTime)
            for mode in res.modes:
                if crtcInfo.mode == mode.id:
                    return round(mode.dot_clock / ((mode.h_total * mode.v_total) or 1), 2)
        return None
    refreshRate = frequency

    @property
    def colordepth(self) -> int:
        return self.screen.root_depth

    @property
    def brightness(self) -> Optional[float]:
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

    @brightness.setter
    def brightness(self, brightness):
        # https://unix.stackexchange.com/questions/150816/how-can-i-lazily-read-output-from-xrandr
        value = brightness / 100
        if 0 <= value <= 1:
            cmd = "xrandr --output %s --brightness %s" % (self.name, str(value))
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
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

    @contrast.setter
    def contrast(self, contrast: int):
        value = contrast / 100
        if 0 <= value <= 1:
            rgb = str(round(contrast, 1))
            gamma = rgb + ":" + rgb + ":" + rgb
            cmd = "xrandr --output %s --gamma %s" % (self.name, gamma)
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
            except:
                pass

    @property
    def mode(self) -> DisplayMode:
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

    @mode.setter
    def mode(self, mode: DisplayMode):
        # https://stackoverflow.com/questions/12706631/x11-change-resolution-and-make-window-fullscreen
        # Xlib.ext.randr.set_screen_size(defaultRootWindow.root, mode.width, mode.height, 0, 0)
        # Xlib.ext.randr.set_screen_config(defaultRootWindow.root, size_id, 0, 0, round(mode.frequency), 0)
        # Xlib.ext.randr.change_output_property()
        allModes = self.allModes
        if mode in allModes:
            cmd = " --mode %sx%s -r %s" % (mode.width, mode.height, round(mode.frequency, 2))
            if self.name and self.name in _XgetAllMonitorsNames():
                cmd = (" --output %s" % self.name) + cmd
            cmd = "xrandr" + cmd
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
            except:
                pass

    def _modeB(self) -> Optional[DisplayMode]:

        outMode: Optional[DisplayMode] = None
        allModes = []
        mode = None

        for crtc in _XgetAllCrtcs(self.name):
            res = crtc[3]
            crtcInfo = crtc[7]
            if crtcInfo.mode:
                mode = crtcInfo.mode
                allModes = res.modes
                break

        if mode and allModes:
            for m in allModes:
                if mode == m.id:
                    outMode = DisplayMode(m.width, m.height,
                                                  round(m.dot_clock / ((m.h_total * m.v_total) or 1), 2))
                    break
        return outMode

    @property
    def defaultMode(self) -> DisplayMode:
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
        _, _ = subprocess.getstatusoutput(cmd)

    @property
    def allModes(self) -> list[DisplayMode]:
        modes: List[DisplayMode] = []
        allModes = []
        for crtcData in _XgetAllCrtcs(self.name):
            display, screen, root, res, output, outputInfo, crtc, crtcInfo = crtcData
            if crtcInfo.mode:
                allModes = res.modes
                break
        for mode in allModes:
            modes.append(DisplayMode(mode.width, mode.height,
                                             round(mode.dot_clock / ((mode.h_total * mode.v_total) or 1), 2)))
        return modes

    @property
    def isPrimary(self) -> bool:
        for monitorData in _XgetAllMonitors(self.name):
            display, root, monitor, monName = monitorData
            return monitor.primary == 1
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
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
            except:
                pass

    def turnOff(self):
        if self.isOn:
            cmd = "xrandr --output %s --off" % self.name
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
            except:
                pass

    def suspend(self):
        # xrandr has no standby option. xset doesn't allow to target just one output (it works at display level)
        cmd = "xset dpms force standby"
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
        except:
            pass

    @property
    def isOn(self) -> bool:
        return self.name in _XgetAllMonitorsNames()

    def attach(self):
        # raise NotImplementedError
        pass
        # This produces the same effect, but requires to keep track of last mode used
        # outputs = __getAllOutputs(name)
        # for outputData in outputs:
        #     display, screen, root, res, output, outputInfo = outputData
        #     if output in _crtcs.keys():
        #         crtcCode, crtcInfo = _crtcs[output]
        #         randr.set_crtc_config(display, crtcCode, Xlib.X.CurrentTime, crtcInfo.x, crtcInfo.y, crtcInfo.mode, crtcInfo.rotation, crtcInfo.outputs)
        #         _crtcs.pop(output)

    def detach(self, permanent: bool = False):
        # raise NotImplementedError
        pass
        # This produces the same effect, but requires to keep track of last mode used
        # outputs = __getAllOutputs(name)
        # for outputData in outputs:
        #     display, screen, root, res, output, outputInfo = outputData
        #     if outputInfo.crtc:
        #         crtcInfo = randr.get_crtc_info(display, outputInfo.crtc, Xlib.X.CurrentTime)
        #         randr.set_crtc_config(display, outputInfo.crtc, Xlib.X.CurrentTime, crtcInfo.x, crtcInfo.y, 0, crtcInfo.rotation, [])
        #         _crtcs[output] = (outputInfo.crtc, crtcInfo)

    @property
    def isAttached(self) -> bool:
        cmd = "xrandr | grep ' connected ' | awk '{ print$1 }'"
        err, ret = subprocess.getstatusoutput(cmd)
        if err != 0:
            ret = []
        return self.name in ret


def _getPrimaryName():
    for monitorData in _XgetAllMonitors():
        display, root, monitor, monName = monitorData
        if monitor.primary == 1 or (monitor.x == 0 and monitor.y == 0):
            return monName
    return None


def _setPrimary(name: str):
    mainMon = _getPrimaryName()
    if name != mainMon:
        cmd = "xrandr --output %s --pos 0x0 --primary --left-of %s" % (name, mainMon)
        try:
            subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
        except:
            pass


def _setPositionTwice(relativePos: Position, relativeTo: Optional[str], name: str):
    # Why it has to be invoked twice? Perhaps there is  an option to commit changes?
    _setPositionTwice(relativePos, relativeTo, name)
    time.sleep(0.5)
    _setPositionTwice(relativePos, relativeTo, name)


def _setPosition(relativePos: Position, relativeTo: Optional[str], name: str):
    if relativePos == PRIMARY:
        _setPrimary(name)

    else:
        monitors = _XgetAllMonitorsDict()
        if name in monitors.keys() and relativeTo in monitors.keys():

            targetMonInfo = monitors[name]["monitor"]
            targetMon = {"relativePos": relativePos, "relativeTo": relativeTo,
                         "pos": Point(targetMonInfo.x, targetMonInfo.y),
                         "size": Size(targetMonInfo.width_in_pixels, targetMonInfo.height_in_pixels)}

            relMonInfo = monitors[relativeTo]["monitor"]
            relMon = {"pos": Point(relMonInfo.x, relMonInfo.y),
                      "size": Size(relMonInfo.width_in_pixels, relMonInfo.height_in_pixels)}

            primaryName = _getPrimaryName()
            # WARNING: There will be no primary monitor when moving it to another position!
            cmd2 = " --noprimary" if name == primaryName else ""
            x, y, relCmd = _getRelativePosition(targetMon, relMon)
            cmd3 = relCmd % relativeTo if relativePos in (LEFT_TOP, RIGHT_TOP, ABOVE_LEFT, BELOW_LEFT) else ""
            cmd = ("xrandr --output %s --pos %sx%s" % (name, x, y)) + cmd2 + cmd3
            try:
                subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)
            except:
                pass


def _XgetAllOutputs(name: str = ""):
    outputs = []
    global _roots
    for rootData in _roots:
        display, screen, root = rootData
        res = randr.get_screen_resources(root)
        for output in res.outputs:
            outputInfo = randr.get_output_info(display, output, res.config_timestamp)
            if not name or (name and name == outputInfo.name):
                outputs.append([display, screen, root, res, output, outputInfo])
    return outputs


def _XgetAllCrtcs(name: str = ""):
    crtcs = []
    for outputData in _XgetAllOutputs():
        display, screen, root, res, output, outputInfo = outputData
        res = randr.get_screen_resources(root)
        for output in res.outputs:
            outputInfo = randr.get_output_info(display, output, res.config_timestamp)
            if not name or (name and name == outputInfo.name):
                for crtc in outputInfo.crtcs:
                    crtcInfo = randr.get_crtc_info(display, crtc, res.config_timestamp)
                    crtcs.append([display, screen, root, res, output, outputInfo, crtc, crtcInfo])
    return crtcs


def _XgetAllMonitors(name: str = ""):
    monitors = []
    global _roots
    for rootData in _roots:
        display, screen, root = rootData
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
        display, screen, root = rootData
        for monitor in randr.get_monitors(root).monitors:
            monitors[display.get_atom_name(monitor.name)] = {"display": display, "root": root, "monitor": monitor}
    return monitors


def _XgetAllMonitorsNames():
    monNames = []
    global _roots
    for rootData in _roots:
        display, screen, root = rootData
        for monitor in randr.get_monitors(root, is_active=True).monitors:
            monNames.append(display.get_atom_name(monitor.name))
    return monNames


def _XgetPrimary():
    outputs = _XgetAllOutputs()
    for monitorData in _XgetAllMonitors():
        display, root, monitor, monName = monitorData
        if monitor.primary == 1 or (monitor.x == 0 and monitor.y == 0):
            for outputData in outputs:
                display, screen, root, res, output, outputInfo = outputData
                if outputInfo.name == monName:
                    handle = output
                    return handle, monName
    return None


def _XgetMonitorData(handle: Optional[int] = None):
    if handle:
        outputs = _XgetAllOutputs()
        for outputData in outputs:
            display, screen, root, res, output, outputInfo = outputData
            if output == handle:
                return display, screen, root, res, output, outputInfo.name
    else:
        outputs = _XgetAllOutputs()
        monitors = _XgetAllMonitors()
        for monitorData in monitors:
            display, root, monitor, monName = monitorData
            if monitor.primary == 1 or len(monitors) == 1:
                for outputData in outputs:
                    display, screen, root, res, output, outputInfo = outputData
                    if outputInfo.crtc:
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
