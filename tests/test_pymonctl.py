#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from typing import Union, Dict

import pymonctl as pmc
from pymonctl.structs import *


def countChanged(names, screensInfo):
    for name in names:
        print("MONITORS COUNT CHANGED:", name, screensInfo[name])


def propsChanged(names, screensInfo):
    for name in names:
        print("MONITORS PROPS CHANGED:", name, screensInfo[name])


print("MONITORS COUNT:", pmc.getMonitorsCount())
print("PRIMARY MONITOR:", pmc.getPrimary().name)
print()
monDict = pmc.getAllMonitorsDict()
for mon in monDict:
    print(monDict[mon])
print()

monitorsPluggged = []
for monitor in pmc.getAllMonitors():
    monitorsPluggged.append(monitor)
    print("NAME", monitor.name)
    print("HANDLE/ID:", monitor.handle)
    print("IS PRIMARY:", monitor.isPrimary)
    print("SIZE:", monitor.size)
    print("POSITION:", monitor.position)
    print("FREQUENCY:", monitor.frequency)
    print("ORIENTATION:", monitor.orientation)
    print("SCALE", monitor.scale)
    print("DPI:", monitor.dpi)
    print("COLOR DEPTH:", monitor.colordepth)
    print("BRIGHTNESS:", monitor.brightness)
    print("CONTRAST:", monitor.contrast)
    print("CURRENT MODE:", monitor.mode)
    print("DEFAULT MODE:", monitor.defaultMode)
    print()


    def pluggedCB(names, info):
        print("MONITOR (UN)PLUGGED!!!")
        print(names)
        print(info)
        print()


    def changedCB(names, info):
        print("MONITOR CHANGED!!!")
        print(names)
        print(info)
        print()


    pmc.enableUpdate(monitorCountChanged=pluggedCB, monitorPropsChanged=changedCB)
    print("CHANGE MODE")
    currMode = monitor.mode
    targetMode = monitor.mode
    modes = monitor.allModes
    for mode in modes:
        if mode.width != monitor.mode.width:
            targetMode = mode
            break
    monitor.mode = targetMode
    time.sleep(3)
    print("SET DEFAULT MODE")
    monitor.setDefaultMode()
    time.sleep(3)
    print("RESTORE MODE")
    monitor.mode = currMode
    print()

    print("CHANGE BRIGHTNESS")
    currBright = monitor.brightness
    monitor.brightness = 50
    time.sleep(2)
    print("RESTORE BRIGHTNESS")
    monitor.brightness = currBright
    print()

    print("CHANGE CONTRAST")
    currContrast = monitor.contrast
    monitor.contrast = 50
    time.sleep(2)
    print("RESTORE CONTRAST")
    monitor.contrast = currContrast
    print()

    print("CHANGE ORIENTATION")
    monitor.orientation = INVERTED
    time.sleep(5)
    print("RESTORE ORIENTATION")
    monitor.orientation = NORMAL
    time.sleep(3)
    print()

    print("IS ON?:", monitor.isOn)
    print("TURN OFF")
    monitor.turnOff()
    time.sleep(5)
    print("IS ON?:", monitor.isOn)
    print("TURN ON")
    monitor.turnOn()
    time.sleep(5)
    print("IS ON?:", monitor.isOn)
    time.sleep(3)
    print("STANDBY")
    monitor.suspend()
    time.sleep(3)
    print("IS ON?:", monitor.isOn)
    print("WAKEUP")
    monitor.turnOn()
    time.sleep(2)
    print("IS ON?:", monitor.isOn)
    print()

    print("IS ATTACHED?:", monitor.isAttached)
    print("DETACH")
    monitor.detach()
    time.sleep(5)
    print("IS ATTACHED?:", monitor.isAttached)
    print("ATTACH")
    monitor.attach()
    time.sleep(2)
    print("IS ATTACHED?:", monitor.isAttached)
    print()
    pmc.disableUpdate()

if len(monitorsPluggged) > 1:
    mon1 = monitorsPluggged[0]
    mon2 = monitorsPluggged[1]
    print("MANAGING MONITORS")
    print("MONITOR 1:", mon1.name)
    print("MONITOR 2:", mon2.name)
    print()
    print("MONITOR 2 AS PRIMARY")
    print("MONITOR 2 PRIMARY:", mon2.isPrimary)
    mon2.setPrimary()
    print("MONITOR 2 PRIMARY:", mon2.isPrimary)
    time.sleep(5)
    print("MONITOR 1 AS PRIMARY")
    print("MONITOR 1 PRIMARY:", mon1.isPrimary)
    mon1.setPrimary()
    print("MONITOR 1 PRIMARY:", mon1.isPrimary)
    print()

    print("CHANGE POSITION OF MONITOR 2 TO BELOW_LEFT")
    mon2.setPosition(BELOW_LEFT, mon1.name)
    print("MONITOR 2 POSITION:", mon2.position)
    while True:
        try:
            time.sleep(0.2)
        except KeyboardInterrupt:
            break
    print()

    print("CHANGE ARRANGEMENT: MONITOR 2 AS PRIMARY, MONITOR 1 AT LEFT_BOTTOM")
    arrangement:  dict[str, dict[str, Union[str, Position, int]]] = {
        mon2.name: {"relativePos": PRIMARY, "relativeTo": None},
        mon1.name: {"relativePos": LEFT_BOTTOM, "relativeTo": mon2.name}
    }
    print(arrangement)
    pmc.arrangeMonitors(arrangement)
    print("MONITOR 1 POSITION:", mon1.position)
    print("MONITOR 2 POSITION:", mon2.position)
    while True:
        try:
            time.sleep(0.2)
        except KeyboardInterrupt:
            break
    print()

    print("CHANGE ARRANGEMENT: MONITOR 1 AS PRIMARY, MONITOR 2 AT RIGHT_TOP")
    arrangement = {
        mon1.name: {"relativePos": PRIMARY, "relativeTo": None},
        mon2.name: {"relativePos": RIGHT_TOP, "relativeTo": mon1.name}
    }
    print(arrangement)
    pmc.arrangeMonitors(arrangement)
    print("MONITOR 1 POSITION:", mon1.position)
    print("MONITOR 2 POSITION:", mon2.position)
