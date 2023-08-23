#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from typing import Union

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

monitorsPlugged = []
for monitor in pmc.getAllMonitors():
    monitorsPlugged.append(monitor)
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


    pmc.enableUpdateInfo()
    pmc.plugListenerRegister(pluggedCB)
    pmc.changeListenerRegister(changedCB)
    currMode = monitor.mode
    targetMode = monitor.mode
    if monitor.size is not None and monitor.defaultMode is not None:
        if monitor.size.width == 5120:
            targetMode = DisplayMode(3840, 1080, monitor.defaultMode.frequency)
        elif monitor.size.width == 1920:
            targetMode = DisplayMode(1360, 768, monitor.defaultMode.frequency)
        elif monitor.size.width == 1680:
            targetMode = DisplayMode(1440, 900, monitor.defaultMode.frequency)
        else:
            modes = monitor.allModes
            for mode in modes:
                if monitor.mode and mode.width != monitor.mode.width:
                    targetMode = mode
                    break
    print("CHANGE MODE", targetMode)
    monitor.setMode(targetMode)
    time.sleep(3)
    print("MODE CHANGED?:", monitor.mode)
    print("SET DEFAULT MODE", monitor.defaultMode)
    monitor.setDefaultMode()
    time.sleep(3)
    print("DEFAULT MODE SET?:", monitor.mode)
    print("RESTORE MODE", currMode)
    monitor.setMode(currMode)
    time.sleep(3)
    print("MODE RESTORED?:", monitor.mode)
    print()

    print("CHANGE BRIGHTNESS")
    currBright = monitor.brightness
    monitor.setBrightness(50)
    time.sleep(2)
    print("RESTORE BRIGHTNESS")
    monitor.setBrightness(currBright)
    time.sleep(2)
    print()

    print("CHANGE CONTRAST")
    currContrast = monitor.contrast
    monitor.setContrast(50)
    time.sleep(2)
    print("RESTORE CONTRAST")
    monitor.setContrast(currContrast)
    time.sleep(2)
    print()

    print("CHANGE ORIENTATION")
    monitor.setOrientation(Orientation.INVERTED)
    time.sleep(5)
    print("RESTORE ORIENTATION")
    monitor.setOrientation(Orientation.NORMAL)
    time.sleep(3)
    print()

    currScale = monitor.scale
    print("CHANGE SCALE. CURRENT:", currScale)
    monitor.setScale((200, 200))
    time.sleep(5)
    print("RESTORE SCALE")
    if currScale is not None:
        monitor.setScale(currScale)

    print("IS ON?:", monitor.isOn)
    print("TURN OFF")
    monitor.turnOff()
    time.sleep(3)
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
    time.sleep(5)
    print("IS ON?:", monitor.isOn)
    print()

    print("IS ATTACHED?:", monitor.isAttached)
    print("DETACH")
    monitor.detach()
    time.sleep(3)
    print("IS ATTACHED?:", monitor.isAttached)
    print("ATTACH")
    monitor.attach()
    time.sleep(5)
    print("IS ATTACHED?:", monitor.isAttached)
    print()
    pmc.disableUpdateInfo()
    pmc.plugListenerUnregister(pluggedCB)
    pmc.changeListenerUnregister(changedCB)

if len(monitorsPlugged) > 1:
    mon1 = monitorsPlugged[0]
    mon2 = monitorsPlugged[1]

    print("MANAGING MONITORS")
    print("MONITOR 1:", mon1.name)
    print("MONITOR 2:", mon2.name)
    print()
    print("MONITOR 2 AS PRIMARY")
    print("MONITOR 2 PRIMARY:", mon2.isPrimary)
    mon2.setPrimary()
    time.sleep(3)
    print("MONITOR 2 PRIMARY:", mon2.isPrimary)
    print("MONITOR 1 AS PRIMARY")
    print("MONITOR 1 PRIMARY:", mon1.isPrimary)
    mon1.setPrimary()
    time.sleep(3)
    print("MONITOR 1 PRIMARY:", mon1.isPrimary)
    print()

    print("CHANGE POSITION OF MONITOR 2 TO BELOW_LEFT")
    mon2.setPosition(Position.BELOW_LEFT, mon1.name)
    time.sleep(0.3)
    print("MONITOR 2 POSITION:", mon2.position)
    print()

    print("=========== size & pos", "MON1", mon1.size, mon1.position, "MON2", mon2.size, mon2.position)

    print("CHANGE ARRANGEMENT: MONITOR 2 AS PRIMARY, MONITOR 1 AT LEFT_BOTTOM")
    arrangement: dict[str, dict[str, Union[str, int, Position, Point, Size]]] = {
        str(mon2.name): {"relativePos": Position.PRIMARY, "relativeTo": ""},
        str(mon1.name): {"relativePos": Position.LEFT_BOTTOM, "relativeTo": mon2.name}
    }
    print(arrangement)
    pmc.arrangeMonitors(arrangement)
    time.sleep(3)

    if mon1.size is not None and mon2.size is not None and mon1.position is not None and mon2.position is not None:
        print("=========== size & pos", "MON1", mon1.size, mon1.position, "MON2", mon2.size, mon2.position)

        print("MONITOR 1 POSITION:", mon1.position, "LEFT_BOTTOM:", mon2.position == Point(mon1.size.width, mon1.size.height - mon2.size.height))
        print("MONITOR 2 POSITION:", mon2.position, "PRIMARY:", mon2.isPrimary)
        print()
        time.sleep(5)

        print("=========== size & pos", "MON1", mon1.size, mon1.position, "MON2", mon2.size, mon2.position)

        print("CHANGE ARRANGEMENT: MONITOR 1 AS PRIMARY, MONITOR 2 AT RIGHT_TOP")
        arrangement = {
            str(mon1.name): {"relativePos": Position.PRIMARY, "relativeTo": ""},
            str(mon2.name): {"relativePos": Position.RIGHT_TOP, "relativeTo": mon1.name}
        }
        print(arrangement)
        pmc.arrangeMonitors(arrangement)
        time.sleep(3)

        print("=========== size & pos", "MON1", mon1.size, mon1.position, "MON2", mon2.size, mon2.position)

        print("MONITOR 1 POSITION:", mon1.position, "PRIMARY:", mon1.isPrimary)
        print("MONITOR 2 POSITION:", mon2.position, "RIGHT_TOP:", mon2.position == Point(mon1.size.width, 0))

        print("=========== size & pos", "MON1", mon1.size, mon1.position, "MON2", mon2.size, mon2.position)


