#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from typing import Union, Optional, List

import pymonctl as pmc


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

monitorsPlugged: List[pmc.Monitor] = []
setAsPrimary: Optional[pmc.Monitor] = None
initArrangement: dict[str, dict[str, pmc.Point]] = {}
for monitor in pmc.getAllMonitors():
    monitorsPlugged.append(monitor)
    initArrangement[monitor.name] = {"relativePos": monitor.position}
    if monitor.isPrimary:
        setAsPrimary = monitor

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
            targetMode = pmc.DisplayMode(3840, 1080, monitor.defaultMode.frequency)
        elif monitor.size.width == 1920:
            targetMode = pmc.DisplayMode(1360, 768, monitor.defaultMode.frequency)
        elif monitor.size.width == 1680:
            targetMode = pmc.DisplayMode(1440, 900, monitor.defaultMode.frequency)
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
    monitor.setOrientation(pmc.Orientation.INVERTED)
    time.sleep(5)
    print("RESTORE ORIENTATION")
    monitor.setOrientation(pmc.Orientation.NORMAL)
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
    print("IS SUSPENDED?:", monitor.isSuspended)
    time.sleep(3)
    print("STANDBY")
    monitor.suspend()
    time.sleep(3)
    print("IS ON?:", monitor.isOn)
    print("IS SUSPENDED?:", monitor.isSuspended)
    print("WAKEUP")
    monitor.turnOn()
    time.sleep(5)
    print("IS ON?:", monitor.isOn)
    print("IS SUSPENDED?:", monitor.isSuspended)
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

print("MANAGING MONITORS")
if len(monitorsPlugged) > 1:
    mon1 = monitorsPlugged[0]
    priNum = "1"
    mon2 = monitorsPlugged[1]
    secNum = "2"
    if setAsPrimary and mon1.name != setAsPrimary.name:
        mon1 = monitorsPlugged[1]
        priNum = "2"
        mon2 = monitorsPlugged[0]
        secNum = "1"

    print("MONITOR 1:", mon1.isPrimary, mon1.position, mon1.size, "MONITOR 2:", mon2.isPrimary, mon2.position, mon2.size)
    print()
    print("MONITOR %s AS PRIMARY" % secNum)
    print("MONITOR 1:", mon1.isPrimary, mon1.position, mon1.size, "MONITOR 2:", mon2.isPrimary, mon2.position, mon2.size)
    mon2.setPrimary()
    time.sleep(3)
    print("MONITOR 1:", mon1.isPrimary, mon1.position, mon1.size, "MONITOR 2:", mon2.isPrimary, mon2.position, mon2.size)
    print("MONITOR %s AS PRIMARY" % priNum)
    mon1.setPrimary()
    time.sleep(3)
    print("MONITOR 1:", mon1.isPrimary, mon1.position, mon1.size, "MONITOR 2:", mon2.isPrimary, mon2.position, mon2.size)
    print()

    print("POSITION MONITOR 2 AT FREE BELOW POSITION (200, -%s)" % mon1.size.height)
    mon2.setPosition((200, mon1.size.height), None)
    print("MONITOR 2 POSITIONED?", mon2.position)
    print()

    print("CHANGE ARRANGEMENT: MONITOR 2 AS PRIMARY, REST OF MONITORS AT LEFT_BOTTOM")
    arrangement: dict[str, dict[str, Union[str, int, pmc.Position, pmc.Point, pmc.Size]]] = {
        str(mon2.name): {"relativePos": pmc.Position.PRIMARY, "relativeTo": ""}
    }
    relativeTo = mon2.name
    for monitor in monitorsPlugged:
        if monitor.name != mon2.name:
            arrangement[str(monitor.name)] = {"relativePos": pmc.Position.LEFT_BOTTOM, "relativeTo": relativeTo}
            relativeTo = monitor.name
    print(arrangement)
    pmc.arrangeMonitors(arrangement)
    time.sleep(3)
    for monitor in monitorsPlugged:
        print("MONITOR", monitor.name, "IS PRIMARY", monitor.isPrimary, "POSITION", monitor.position, "SIZE", monitor.size)
    print()

    print("CHANGE ARRANGEMENT: MONITOR 1 AS PRIMARY, REST OF MONITORS AT RIGHT_TOP")
    arrangement = {
        str(mon1.name): {"relativePos": pmc.Position.PRIMARY, "relativeTo": ""}
    }
    relativeTo = mon1.name
    for monitor in monitorsPlugged:
        if monitor.name != mon1.name:
            arrangement[str(monitor.name)] = {"relativePos": pmc.Position.RIGHT_TOP, "relativeTo": relativeTo}
            relativeTo = monitor.name
    print(arrangement)
    pmc.arrangeMonitors(arrangement)
    time.sleep(3)
    for monitor in monitorsPlugged:
        print("MONITOR", monitor.name, "IS PRIMARY", monitor.isPrimary, "POSITION", monitor.position, "SIZE", monitor.size)
    print()

    if initArrangement:
        print("RESTORE INITIAL MONITOR CONFIG")
        print(initArrangement)
        pmc.arrangeMonitors(initArrangement)
        if setAsPrimary is not None:
            setAsPrimary.setPrimary()
