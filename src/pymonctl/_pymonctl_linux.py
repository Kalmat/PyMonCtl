#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys

assert sys.platform == "linux"

import math
import os
from typing import Optional, List, Tuple

import Xlib.display
import Xlib.X
import Xlib.ext.randr

from pymonctl._xlibcontainer import Props, defaultRootWindow, getProperty, getPropertyValue
from pymonctl import Structs, _pointInBox


def __getDisplays() -> List[Xlib.display.Display]:
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


def __getRoots():
    for display in __getDisplays():
        for i in range(display.screen_count()):
            try:
                screen = display.screen(i)
                yield [display, screen, screen.root]
            except:
                continue


def __getAllOutputs(name: str = ""):
    for rootData in __getRoots():
        display, screen, root = rootData
        res = root.xrandr_get_screen_resources()
        for output in res.outputs:
            outputInfo = display.xrandr_get_output_info(output, res.config_timestamp)
            if not name or (name and name == outputInfo.name):
                yield [display, screen, root, res, outputInfo]


def __getAllCrtcs(name: str = ""):
    for rootData in __getAllOutputs():
        display, screen, root, res, outputInfo = rootData
        res = root.xrandr_get_screen_resources()
        for output in res.outputs:
            outputInfo = display.xrandr_get_output_info(output, res.config_timestamp)
            if not name or (name and name == outputInfo.name):
                for crtc in outputInfo.crtcs:
                    crtcInfo = defaultRootWindow.display.xrandr_get_crtc_info(crtc, res.config_timestamp)
                    yield [display, screen, root, res, output, outputInfo, crtc, crtcInfo]


def __getAllMonitors():
    for rootData in __getRoots():
        display, screen, root = rootData
        for monitor in root.xrandr_get_monitors().monitors:
            yield [display, root, monitor, display.get_atom_name(monitor.name)]


def __getMonitorsNames():
    for rootData in __getRoots():
        display, screen, root = rootData
        for monitor in root.xrandr_get_monitors().monitors:
            yield display.get_atom_name(monitor.name)


def _getAllScreens():
    # https://stackoverflow.com/questions/8705814/get-display-count-and-resolution-for-each-display-in-python-without-xrandr
    # https://www.x.org/releases/X11R7.7/doc/libX11/libX11/libX11.html#Obtaining_Information_about_the_Display_Image_Formats_or_Screens
    # https://github.com/alexer/python-xlib/blob/master/examples/xrandr.py
    result: dict[str, Structs.ScreenValue] = {}

    for crtc in __getAllCrtcs():
        display, screen, root, res, output, outputInfo, crtcNumber, crtcInfo = crtc

        if crtcInfo.mode:
            name = outputInfo.name
            dId = output
            x, y, w, h = crtcInfo.x, crtcInfo.y, crtcInfo.width, crtcInfo.height
            wa: List[int] = getPropertyValue(getProperty(window=root, prop=Props.Root.WORKAREA.value, display=display), display=display)
            wx, wy, wr, wb = x + wa[0], y + wa[1], x + w - (crtcInfo.width - wa[2] - wa[0]), y + h - (crtcInfo.height - wa[3] - wa[1])
            try:
                dpiX, dpiY = round(crtcInfo.width * 25.4 / outputInfo.mm_width), round(crtcInfo.height * 25.4 / outputInfo.mm_height)
            except:
                try:
                    dpiX, dpiY = round(w * 25.4 / screen.width_in_mms), round(h * 25.4 / screen.height_in_mms)
                except:
                    dpiX = dpiY = 0
            scaleX, scaleY = round(dpiX / 96 * 100), round(dpiY / 96 * 100)
            rot = int(math.log(crtcInfo.rotation, 2))
            freq = 0.0
            for mode in res.modes:
                if crtcInfo.mode == mode.id:
                    freq = mode.dot_clock / ((mode.h_total * mode.v_total) or 1)
                    break
            depth = screen.root_depth

            result[name] = {
                'id': dId,
                'is_primary': (x, y) == (0, 0),
                'pos': Structs.Point(x, y),
                'size': Structs.Size(w, h),
                'workarea': Structs.Rect(wx, wy, wr, wb),
                'scale': (scaleX, scaleY),
                'dpi': (dpiX, dpiY),
                'orientation': rot,
                'frequency': freq,
                'colordepth': depth
            }
    return result


def _getMonitorsCount() -> int:
    monitors = [__getAllMonitors()]
    count = len(monitors)
    if count == 0:
        count = len(defaultRootWindow.root.xrandr_get_monitors().monitors)
    return count


def _getScreenSize(name: str = "") -> Optional[Structs.Size]:
    res: Optional[Structs.Size] = None
    if name:
        for mon in __getAllMonitors():
            monitor = mon[2]
            monName = mon[3]
            if monName == name:
                size: Tuple[int, int] = monitor.width_in_pixels, monitor.height_in_pixels
                res = Structs.Size(*size)
                break
    else:
        size = defaultRootWindow.getDesktopGeometry()
        res = Structs.Size(*size)
    return res


def _getWorkArea(name: str = "") -> Optional[Structs.Rect]:
    res: Optional[Structs.Rect] = None
    if name:
        for mon in __getAllMonitors():
            display, root, monitor, monName = mon
            if monName == name:
                x, y, w, h = monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels
                wa: List[int] = getPropertyValue(getProperty(window=root, prop=Props.Root.WORKAREA.value, display=display), display=display)
                wx, wy, wr, wb = x + wa[0], y + wa[1], x + w - (w - wa[2] - wa[0]), y + h - (h - wa[3] - wa[1])
                res = Structs.Rect(wx, wy, wr, wb)
                break
    else:
        wa = defaultRootWindow.getWorkArea()
        res = Structs.Rect(wa[0], wa[1], wa[2], wa[3])
    return res


def _getPosition(name: str = "") -> Optional[Structs.Point]:
    pos: Optional[Structs.Point] = None
    for mon in __getAllMonitors():
        monitor = mon[2]
        monName = mon[3]
        if (not name and monitor.primary == 1) or (name and monName == name):
            pos = Structs.Point(monitor.x, monitor.y)
            break
    return pos


def _getRect(name: str = "") -> Optional[Structs.Rect]:
    rect: Optional[Structs.Rect] = None
    for mon in __getAllMonitors():
        monitor = mon[2]
        monName = mon[3]
        if (not name and monitor.primary == 1) or (name and monName == name):
            rect = Structs.Rect(monitor.x, monitor.y, monitor.x + monitor.width_in_pixels, monitor.y + monitor.height_in_pixels)
            break
    return rect


def _findMonitorName(x: int, y: int) -> str:
    name: str = ""
    for mon in __getAllMonitors():
        monitor = mon[2]
        monName = mon[3]
        sx, sy, sw, sh = monitor.x, monitor.y, monitor.width_in_pixels, monitor.height_in_pixels
        if _pointInBox(x, y, sx, sy, sw, sh):
            name = monName
            break
    return name


def _getCurrentMode(name: str = "") -> Optional[Structs.DisplayMode]:

    outMode: Optional[Structs.DisplayMode] = None
    allModes = []
    mode = None

    if name:
        for crtc in __getAllCrtcs(name):
            res = crtc[3]
            crtcInfo = crtc[7]
            if crtcInfo.mode:
                mode = crtcInfo.mode
                allModes = res.modes
                break
    else:
        root = defaultRootWindow.root
        res = root.xrandr_get_screen_resources()
        for output in res.outputs:
            outputInfo = defaultRootWindow.display.xrandr_get_output_info(output, res.config_timestamp)
            for crtc in outputInfo.crtcs:
                crtcInfo = defaultRootWindow.display.xrandr_get_crtc_info(crtc, res.config_timestamp)
                if crtcInfo.mode:
                    mode = crtcInfo.mode
                    allModes = res.modes
                    break
            if mode: break

    if mode and allModes:
        for m in allModes:
            if mode == m.id:
                outMode = Structs.DisplayMode(m.width, m.height, m.dot_clock / ((m.h_total * m.v_total) or 1))
                break
    return outMode


def __getAllowedModesID(name: str = "") -> List[Tuple[int, Structs.DisplayMode]]:

    modes: List[Tuple[int, Structs.DisplayMode]] = []
    allModes = []

    if name:
        for crtc in __getAllCrtcs(name):
            res = crtc[3]
            allModes = res.modes
            break
    else:
        root = defaultRootWindow.root
        res = root.xrandr_get_screen_resources()
        allModes = res.modes

    for mode in allModes:
        modes.append((mode.id, Structs.DisplayMode(mode.width, mode.height, mode.dot_clock / ((mode.h_total * mode.v_total) or 1))))
    return modes


def _getAllowedModes(name: str = "") -> List[Structs.DisplayMode]:

    modes: List[Structs.DisplayMode] = []
    allModes = []

    if name:
        for crtc in __getAllCrtcs(name):
            res = crtc[3]
            crtcInfo = crtc[7]
            if crtcInfo.mode:
                allModes = res.modes
                break
    else:
        root = defaultRootWindow.root
        res = root.xrandr_get_screen_resources()
        allModes = res.modes

    for mode in allModes:
        modes.append(Structs.DisplayMode(mode.width, mode.height, mode.dot_clock / ((mode.h_total * mode.v_total) or 1)))
    return modes


# def _eventLoop(kill: threading.Event, interval: float):
#
#     pp = pprint.PrettyPrinter(indent=4)
#
#     defaultRootWindow.root.xrandr_select_input(
#         Xlib.ext.randr.RRScreenChangeNotifyMask
#         | Xlib.ext.randr.RRCrtcChangeNotifyMask
#         | Xlib.ext.randr.RROutputChangeNotifyMask
#         | Xlib.ext.randr.RROutputPropertyNotifyMask
#     )
#
#     while not kill.is_set():
#
#         count = defaultRootWindow.display.pending_events()
#         while count > 0 and not kill.is_set():
#
#             e = defaultRootWindow.display.next_event()
#
#             if e.__class__.__name__ == Xlib.ext.randr.ScreenChangeNotify.__name__:
#                 print('Screen change')
#                 print(pp.pprint(e._data))
#
#             # check if we're getting one of the RandR event types with subcodes
#             elif e.type == defaultRootWindow.display.extension_event.CrtcChangeNotify[0]:
#                 # yes, check the subcodes
#
#                 # CRTC information has changed
#                 if (e.type, e.sub_code) == defaultRootWindow.display.extension_event.CrtcChangeNotify:
#                     print('CRTC change')
#                     # e = randr.CrtcChangeNotify(display=display.display, binarydata = e._binary)
#                     print(pp.pprint(e._data))
#
#                 # Output information has changed
#                 elif (e.type, e.sub_code) == defaultRootWindow.display.extension_event.OutputChangeNotify:
#                     print('Output change')
#                     # e = randr.OutputChangeNotify(display=display.display, binarydata = e._binary)
#                     print(pp.pprint(e._data))
#
#                 # Output property information has changed
#                 elif (e.type, e.sub_code) == defaultRootWindow.display.extension_event.OutputPropertyNotify:
#                     print('Output property change')
#                     # e = randr.OutputPropertyNotify(display=display.display, binarydata = e._binary)
#                     print(pp.pprint(e._data))
#                 else:
#                     print("Unrecognised subcode", e.sub_code)
#
#             count -= 1
#         kill.wait(interval)


def _changeMode(mode: Structs.DisplayMode, name: str = ""):
    # https://stackoverflow.com/questions/12706631/x11-change-resolution-and-make-window-fullscreen
    # Xlib.ext.randr.set_screen_size(defaultRootWindow.root, mode.width, mode.height, 0, 0)
    # Xlib.ext.randr.set_screen_config(defaultRootWindow.root, size_id, 0, 0, round(mode.frequency), 0)
    # Xlib.ext.randr.change_output_property()
    allModes = _getAllowedModes(name)
    if mode in allModes:
        cmd = " -s %sx%s -r %s" % (mode.width, mode.height, round(mode.frequency))
        if name and name in __getMonitorsNames():
            cmd = (" --output %s" % name) + cmd
            # cmd = (" --screen %s" % 0) + cmd
        cmd = "xrandr" + cmd
        ret = subprocess.check_output(cmd, shell=True).decode(encoding="utf-8").replace("\n", "")


def _changeScale(scale: int, name: str = ""):
    pass


def _changeOrientation(orientation: int, name: str = ""):
    pass


def _changePosition(newX: int, newY: int, name: str = ""):
    pass


def _getMousePos() -> Structs.Point:
    """
    Get the current (x, y) coordinates of the mouse pointer on screen, in pixels

    :return: Point struct
    """
    mp = defaultRootWindow.root.query_pointer()
    return Structs.Point(mp.root_x, mp.root_y)
