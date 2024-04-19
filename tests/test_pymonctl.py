#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from typing import Union, Optional, List, Tuple, cast

import pymonctl as pmc


_TIMELAP = 5


def pluggedCB(names: List[str], info: dict[str, pmc.ScreenValue]):
    print("MONITOR (UN)PLUGGED!!!")
    print(names)
    print(info)
    print()


def changedCB(names: List[str], info: dict[str, pmc.ScreenValue]):
    print("MONITOR CHANGED!!!")
    print(names)
    print(info)
    print()


print("MONITORS COUNT:", pmc.getMonitorsCount())
print("PRIMARY MONITOR:", pmc.getPrimary().name)
print()
monDict = pmc.getAllMonitorsDict()
for mon in monDict:
    print(monDict[mon])
print()

monitorsPlugged: List[pmc.Monitor] = pmc.getAllMonitors()
initArrangement: List[Tuple[pmc.Monitor, pmc.ScreenValue]] = []
initDict: dict[str, dict[str, Optional[Union[str, int, pmc.Position, pmc.Point, pmc.Size]]]] = {}
setAsPrimary: Optional[pmc.Monitor] = None
try:
    initArrangement = pmc.saveSetup()
    print("INITIAL POSITIONS:", initArrangement)
except:
    for monitor in monitorsPlugged:
        initDict[monitor.name] = {"relativePos": cast(pmc.Point, monitor.position)}
        if monitor.isPrimary:
            setAsPrimary = monitor
    print("INITIAL POSITIONS:", initDict)
print()


for monitor in monitorsPlugged:

    if monitor.isPrimary and setAsPrimary is None:
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
    print("ALL MODES:", monitor.allModes)
    print()

    print("WATCHDOG ENABLED", pmc.isWatchdogEnabled())
    pmc.enableUpdateInfo()
    print("UPDATE ENABLED", pmc.isUpdateInfoEnabled())
    pmc.plugListenerRegister(pluggedCB)
    print("PLUG LISTENER REGISTERED", pmc.isPlugListenerRegistered(pluggedCB))
    pmc.changeListenerRegister(changedCB)
    print("CHANGE LISTENER REGISTERED", pmc.isChangeListenerRegistered(changedCB))
    print("WATCHDOG ENABLED", pmc.isWatchdogEnabled())
    print()

    currMode = monitor.mode
    targetMode = None
    if currMode is not None:
        monWidth = currMode.width
        targetWidth = monWidth
        if monWidth == 5120:
            targetWidth = 3840
        elif monWidth == 3840:
            targetWidth = 2560
        elif monWidth == 1920:
            targetWidth = 1360
        elif monWidth == 1680:
            targetWidth = 1280
        elif monWidth == 1470:
            targetWidth = 1710
        for mode in monitor.allModes:
            if targetWidth == mode.width:
                targetMode = mode
                break
            elif (not targetMode or mode.width > targetMode.width) and mode.width != currMode.width:
                targetMode = mode
        if not targetMode:
            targetMode = currMode
    print("CHANGE MODE", "Current:", currMode, " / Target:", targetMode)
    monitor.setMode(targetMode)
    time.sleep(_TIMELAP)
    print("MODE CHANGED?:", "Current:", monitor.mode)
    print("SET DEFAULT MODE", "Target:", monitor.defaultMode)
    monitor.setDefaultMode()
    time.sleep(_TIMELAP)
    print("DEFAULT MODE SET?:", "Current:", monitor.mode)
    print("RESTORE MODE", "Target:", currMode)
    monitor.setMode(currMode)
    time.sleep(_TIMELAP)
    print("MODE RESTORED?:", "Current:", monitor.mode)
    print()

    currBright = monitor.brightness
    print("CHANGE BRIGHTNESS", "Current:", currBright, "Target:", 50)
    monitor.setBrightness(50)
    time.sleep(_TIMELAP)
    print("RESTORE BRIGHTNESS", "Current:", monitor.brightness, "Target:", currBright)
    monitor.setBrightness(currBright)
    time.sleep(_TIMELAP)
    print()

    currContrast = monitor.contrast
    print("CHANGE CONTRAST", "Current:", currContrast, "Target:", 50)
    monitor.setContrast(50)
    time.sleep(_TIMELAP)
    print("RESTORE CONTRAST", "Current:", monitor.contrast, "Target:", currContrast)
    monitor.setContrast(currContrast)
    time.sleep(_TIMELAP)
    print()

    orientation = monitor.orientation
    print("CHANGE ORIENTATION", "Current:", orientation*90 if orientation is not None else None, "Target:", pmc.Orientation.INVERTED*90)
    monitor.setOrientation(pmc.Orientation.INVERTED)
    time.sleep(_TIMELAP*2)
    orientation = monitor.orientation
    print("RESTORE ORIENTATION", "Current:", orientation*90 if orientation is not None else None, "Target:", pmc.Orientation.NORMAL)
    monitor.setOrientation(pmc.Orientation.NORMAL)
    time.sleep(_TIMELAP*2)
    print()

    currScale = monitor.scale
    print("CHANGE SCALE", "Current:", currScale, "Target:", 200)
    monitor.setScale((200, 200))
    time.sleep(_TIMELAP*2)
    print("SCALE CHANGED (Not all scale values will be allowed, setting nearest)?:", "Current:", monitor.scale)
    print("RESTORE SCALE", "Target:", currScale)
    if currScale is not None:
        monitor.setScale(currScale)
    time.sleep(_TIMELAP)
    print("SCALE RESTORED?:", "Current:", monitor.scale)

    print("IS ON?:", monitor.isOn)
    print("TURN OFF")
    monitor.turnOff()
    time.sleep(_TIMELAP)
    print("IS ON?:", monitor.isOn)
    print("TURN ON")
    monitor.turnOn()
    time.sleep(_TIMELAP*2)
    print("IS ON?:", monitor.isOn)
    print("IS SUSPENDED?:", monitor.isSuspended)
    print("STANDBY")
    monitor.suspend()
    time.sleep(_TIMELAP*2)
    print("IS ON?:", monitor.isOn)
    print("IS SUSPENDED?:", monitor.isSuspended)
    print("WAKEUP")
    monitor.turnOn()
    time.sleep(_TIMELAP*2)
    print("IS ON?:", monitor.isOn)
    print("IS SUSPENDED?:", monitor.isSuspended)
    print()

    print("IS ATTACHED?:", monitor.isAttached)
    print("DETACH")
    monitor.detach()
    time.sleep(_TIMELAP)
    print("IS ATTACHED?:", monitor.isAttached)
    print("ATTACH")
    monitor.attach()
    time.sleep(_TIMELAP*2)
    print("IS ATTACHED?:", monitor.isAttached)
    print()
    pmc.disableUpdateInfo()
    print("UPDATE ENABLED", pmc.isUpdateInfoEnabled())
    pmc.plugListenerUnregister(pluggedCB)
    print("PLUG LISTENER REGISTERED", pmc.isPlugListenerRegistered(pluggedCB))
    pmc.changeListenerUnregister(changedCB)
    print("CHANGE LISTENER REGISTERED", pmc.isChangeListenerRegistered(changedCB))
    print("WATCHDOG ENABLED", pmc.isWatchdogEnabled())

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
    time.sleep(_TIMELAP)
    print("MONITOR 1:", mon1.isPrimary, mon1.position, mon1.size, "MONITOR 2:", mon2.isPrimary, mon2.position, mon2.size)
    print("MONITOR %s AS PRIMARY" % priNum)
    mon1.setPrimary()
    time.sleep(_TIMELAP)
    print("MONITOR 1:", mon1.isPrimary, mon1.position, mon1.size, "MONITOR 2:", mon2.isPrimary, mon2.position, mon2.size)
    print()

    size = mon1.size
    if size:
        print("POSITION MONITOR 2 AT FREE BELOW POSITION (200, %s)" % size.height)
        mon2.setPosition((200, size.height), None)
        time.sleep(_TIMELAP)
        print("MONITOR 2 POSITIONED?", mon2.position)
        print()

    print("CHANGE ARRANGEMENT: MONITOR 2 AS PRIMARY, REST OF MONITORS AT LEFT_BOTTOM")
    arrangement: dict[str, dict[str, Union[str, int, pmc.Position, pmc.Point, pmc.Size, None]]] = {
        str(mon2.name): {"relativePos": pmc.Position.PRIMARY, "relativeTo": ""}
    }
    relativeTo = mon2.name
    for monitor in monitorsPlugged:
        if monitor.name != mon2.name:
            arrangement[str(monitor.name)] = {"relativePos": pmc.Position.LEFT_BOTTOM, "relativeTo": relativeTo}
            relativeTo = monitor.name
    print(arrangement)
    pmc.arrangeMonitors(arrangement)
    time.sleep(_TIMELAP)
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
    time.sleep(_TIMELAP)
    for monitor in monitorsPlugged:
        print("MONITOR", monitor.name, "IS PRIMARY", monitor.isPrimary, "POSITION", monitor.position, "SIZE", monitor.size)
    print()

    if initArrangement:
        print("RESTORE INITIAL MONITOR CONFIG")
        print(initArrangement)
        pmc.restoreSetup(initArrangement)
    elif initDict:
        print("RESTORE INITIAL MONITOR CONFIG")
        print(initDict)
        pmc.arrangeMonitors(initDict)
        if setAsPrimary is not None:
            setAsPrimary.setPrimary()
