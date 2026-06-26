# PyMonCtl
[![CI](https://github.com/Kalmat/PyMonCtl/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/Kalmat/PyMonCtl/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/PyMonCtl.svg)](https://badge.fury.io/py/PyMonCtl)
[![Documentation Status](https://readthedocs.org/projects/PyMonCtl/badge/?version=latest)](https://PyMonCtl.readthedocs.io/en/latest/?badge=latest)
[![Downloads](https://static.pepy.tech/badge/PyMonCtl/month)](https://pepy.tech/project/PyMonCtl)
[![Stars](https://img.shields.io/github/stars/Kalmat/PyMonCtl?style=flat)](https://github.com/Kalmat/PyMonCtl/stargazers)
[![License](https://img.shields.io/badge/license-BSD%203--Clause-blue)](LICENSE.txt)

**Cross-platform monitor detection and management for Python.** PyMonCtl provides a consistent way to work with system displays - across Windows, macOS, and Linux - with a simple, unified API.

It is designed for developers building tools that need to understand or adapt to multi-monitor environments.

---

## Why PyMonCtl

Working with multiple monitors usually requires platform-specific code. PyMonCtl aims to reduce that complexity by offering a unified interface for:
* Querying display configuration
* Understanding multi-monitor layouts
* Responding in real-time to display changes
* Integrating monitor information into automation workflows
* Manage complex, dynamic multi-monitor setups and their persistence

---

## Features

### Monitor inspection
* Connected displays enumeration
* Resolution, DPI, scaling
* Physical layout coordinates
* Primary monitor detection

### Layout awareness
* Multi-monitor spatial relationships
* Virtual desktop positioning
* Dynamic custom multi-monitor layouts

### System events
* Monitor plug/unplug detection
* Configuration change monitoring

### Persistence
* Save current layout
* Restore previous setups

---

## Examples

**Get primary monitor and basic info on all other present monitors**


```python
import pymonctl as pmc

monitors = pmc.getAllMonitors()

primary = pmc.getPrimary()

print("Primary:", primary.name)

for m in monitors:
    print(m.name, m.position, m.size)
```

**Change multi-monitor layout when a given application is open, restoring previous one when it is closed**

```python
import pymonctl as pmc
import PyMonCtl as pwc
import time

# Default layout (first monitor as Primary, second monitor aligned to the right and top sides of primary) 
_DEFAULT_LAYOUT = {
    'Display1': {'relativePos': pmc.Position.PRIMARY, 'relativeTo': ''}, 
    'Display2': {'relativePos': pmc.Position.RIGHT_TOP, 'relativeTo': 'Display1'}
}
# Custom layout (second monitor as Primary, first monitor aligned on top and left sides of primary)
_OBS_LAYOUT = {
    'Display2': {'relativePos': pmc.Position.PRIMARY, 'relativeTo': ''}, 
    'Display1': {'relativePos': pmc.Position.ABOVE_RIGHT, 'relativeTo': 'Display2'}
}

 # callback function to be invoked when window closes
def on_closed(is_alive: bool) -> None:
    # window has been closed. Apply default multi-monitor layout
    pmc.arrangeMonitors(_DEFAULT_LAYOUT)

win = None
# Search for given window
while not win:
    time.sleep(0.2)
    windows = pwc.getWindowsWithTitle("OBS Studio", None, pwc.Re.CONTAINS)
    if windows:
        # window found
        win = windows[0]
        # start watchdog to detect when window closes
        win.watchdog.start(isAliveCB=on_closed)
        # apply custom multi-monitor layout
        pmc.arrangeMonitors(_OBS_LAYOUT)
```

---

## Ecosystem

PyMonCtl is often used alongside:
* PyMonCtl → window management
* PyWinBox → geometry utilities

Together they allow building higher-level desktop automation, screen recording tools, GUI testing, 
display and window monitoring or tiling, kiosks, overlays, and multi-monitor workflows

---

## General Features

Functions to get monitor instances, get info and arrange monitors plugged to the system.

|                        General functions:                        |
|:----------------------------------------------------------------:|
|          [getAllMonitors](docs/docstrings.md#getallmonitors)          |
|      [getAllMonitorsDict](docs/docstrings.md#getallmonitorsdict)      |
|        [getMonitorsCount](docs/docstrings.md#getmonitorscount)        |
|              [getPrimary](docs/docstrings.md#getprimary)              |
|     [findMonitorsAtPoint](docs/docstrings.md#findmonitorsatpoint)     |
| [findMonitorsAtPointInfo](docs/docstrings.md#findmonitorsatpointinfo) |
|     [findMonitorWithName](docs/docstrings.md#findmonitorwithname)     |
| [findMonitorWithNameInfo](docs/docstrings.md#findmonitorwithnameinfo) |
|               [saveSetup](docs/docstrings.md#savesetup)               |
|            [restoreSetup](docs/docstrings.md#restoresetup)            |
|         [arrangeMonitors](docs/docstrings.md#arrangemonitors)         |
|             [getMousePos](docs/docstrings.md#getmousepos)             |


## Monitor Class

Class to access all methods and functions to get info and control a given monitor plugged to the system.

This class is not meant to be directly instantiated. Instead, use convenience functions like `getAllMonitors()`,
`getPrimary()` or `findMonitorsAtPoint(x, y)`. Use [PyMonCtl](https://github.com/Kalmat/PyMonCtl) module in case you need to 
find the monitor a given window is on, by using `name = window.getMonitor()` method which returns the name of the monitor that
can directly be used to invoke `findMonitorWithName(name)` function.

To instantiate it, you need to pass the monitor handle (OS-dependent). It can raise ValueError exception in case 
the provided handle is not valid.

|                    Methods                     | Windows | Linux | macOS |
|:----------------------------------------------:|:-------:|:-----:|:-----:|
|           [size](docs/docstrings.md#size)           |    X    |   X   |   X   |
|       [workarea](docs/docstrings.md#workarea)       |    X    |   X   |   X   |
|       [position](docs/docstrings.md#position)       |    X    |   X   |   X   |
|    [setPosition](docs/docstrings.md#setposition)    |    X    |   X   |   X   |
|            [box](docs/docstrings.md#box)            |    X    |   X   |   X   |
|           [rect](docs/docstrings.md#rect)           |    X    |   X   |   X   |
|      [frequency](docs/docstrings.md#frequency)      |    X    |   X   |   X   |
|     [colordepth](docs/docstrings.md#colordepth)     |    X    |   X   |   X   |
|            [dpi](docs/docstrings.md#dpi)            |    X    |   X   |   X   |
|          [scale](docs/docstrings.md#scale)          |    X    |   X   |   X   |
|       [setScale](docs/docstrings.md#setscale)       |    X    |   X   |   X   |
|    [orientation](docs/docstrings.md#orientation)    |    X    |   X   |   X   |
| [setOrientation](docs/docstrings.md#setorientation) |    X    |   X   | X (1) |
|     [brightness](docs/docstrings.md#brightness)     |  X (2)  |   X   |   X   |
|  [setBrightness](docs/docstrings.md#setbrightness)  |  X (2)  |   X   |   X   |
|       [contrast](docs/docstrings.md#contrast)       |  X (2)  | X (3) | X (3) |
|    [setContrast](docs/docstrings.md#setcontrast)    |  X (2)  | X (3) | X (3) |
|           [mode](docs/docstrings.md#mode)           |    X    |   X   |   X   |
|        [setMode](docs/docstrings.md#setmode)        |    X    |   X   |   X   |
|    [defaultMode](docs/docstrings.md#defaultmode)    |    X    |   X   |   X   |
| [setDefaultMode](docs/docstrings.md#setdefaultmode) |    X    |   X   |   X   |
|       [allModes](docs/docstrings.md#allmodes)       |    X    |   X   |   X   |
|     [setPrimary](docs/docstrings.md#setprimary)     |    X    |   X   |   X   |
|      [isPrimary](docs/docstrings.md#isprimary)      |    X    |   X   |   X   |
|         [turnOn](docs/docstrings.md#turnon)         |  X (4)  |   X   | X (4) |
|        [turnOff](docs/docstrings.md#turnoff)        |  X (4)  |   X   | X (4) |
|           [isOn](docs/docstrings.md#ison)           |  X (2)  |   X   |   X   |
|        [suspend](docs/docstrings.md#suspend)        |  X (4)  | X (4) | X (4) |
|    [isSuspended](docs/docstrings.md#issuspended)    |  X (2)  |   X   |   X   |
|         [attach](docs/docstrings.md#attach)         |    X    |   X   |       |
|         [detach](docs/docstrings.md#detach)         |    X    |   X   |       |
|     [isAttached](docs/docstrings.md#isattached)     |    X    |   X   |   X   |


(1) Maybe not working in all macOS versions and/or architectures (thanks to University of [Utah - Marriott Library - Apple Infrastructure](https://github.com/univ-of-utah-marriott-library-apple/privacy_services_manager), [eryksun](https://stackoverflow.com/questions/22841741/calling-functions-with-arguments-from-corefoundation-using-ctypes) and [nriley](https://github.com/nriley/brightness/blob/master/brightness.c) for pointing me to the solution)

(2) If monitor has no VCP MCCS support, these methods won't likely work.

(3) It doesn't exactly return / change contrast, but gamma values.

(4) Different behavior according to OS:
- Windows: Working with VCP MCCS support only.
- Linux: It will suspend ALL monitors. To address just one monitor, try using turnOff() / turnOn() / detach() / attach() methods.
- macOS: It will suspend ALL monitors. Use turnOn() to wake them up again


***WARNING: Most of these properties may return ''None'' in case the value can not be obtained***

### Important OS-dependent behaviors and limitations:

  - Windows:
      - Primary monitor is mandatory, and it is always placed at (0, 0) coordinates. 
      - Monitors can not overlap.
      - To set a monitor as Primary, it is necessary to reposition primary monitor first, so the rest of monitors will sequentially be repositioned to RIGHT_TOP.
      - If you attach / detach / plug / unplug a monitor, all IDs may change. The module will try to refresh the IDs for all Monitor class instances, but take into account it may fail!
  - Linux:
      - Primary monitor can be anywhere, and even there can be no primary monitor. 
      - Monitors can overlap, so take this into account when setting a new monitor position. 
      - xrandr won't accept negative values, so the whole setup will be referenced to (0, 0) coordinates.
      - xrandr will sort primary monitors first. Because of this and for homogeneity, when positioning a monitor as primary (only with setPosition() method), it will be placed at (0 ,0) and all the rest to RIGHT_TOP.
  - macOS:
      - Primary monitor is mandatory, and it is always placed at (0, 0) coordinates. 
      - Monitors can overlap, so take this into account when setting a new monitor position. 
      - To set a monitor as Primary, it is necessary to reposition primary monitor first, so the rest of monitors will sequentially be repositioned to RIGHT_TOP.
      - setScale() method uses a workaround by applying the nearest monitor mode to magnify text to given value

It is highly recommended to use `arrangeMonitors()` function for complex setups or just in case there are two or more monitors.   

---

## Keep track of Monitor(s) changes

You can activate a watchdog, running in a separate Thread, which will allow you to keep monitors 
information updated, without negatively impacting your main process, and define hooks and its callbacks to be 
notified when monitors are plugged / unplugged or their properties change.

|                       Watchdog methods:                        |
|:--------------------------------------------------------------:|
|      [isWatchdogEnabled](docs/docstrings.md#iswatchdogenabled)      |
| [updateWatchdogInterval](docs/docstrings.md#updatewatchdoginterval) |

The watchdog will automatically start while the update information is enabled and / or there are any listeners 
registered, and will automatically stop otherwise or if the script finishes.

You can check if the watchdog is working (`isWatchdogEnabled()`) and also change its update interval 
(`updateWatchdogInterval()`) in case you need a custom period (default is 0.5 seconds). Adjust this value to your needs, 
but take into account that higher values will take longer to detect and notify changes; whilst lower values will 
consume more CPU and may produce additional notifications for intermediate (non-final) status.

### Keep Monitors info updated

|                   Info update methods:                    |
|:---------------------------------------------------------:|
|    [enableUpdateInfo](docs/docstrings.md#enableupdateinfo)     |
|   [disableUpdateInfo](docs/docstrings.md#disableupdateinfo)    |
| [isUpdateInfoEnabled](docs/docstrings.md#isupdateinfoenabled)  |

Enable this only if you need to keep track of monitor-related events like changing its resolution, position, scale,
or if monitors can be dynamically plugged or unplugged in a multi-monitor setup. If you need monitors info updated 
at a given moment, but not continuously updated, just invoke `getAllMonitors()` at your convenience.

If enabled, it will activate a separate thread which will periodically update the list of monitors and
their properties (see `getAllMonitors()` and `getAllMonitorsDict()` function).

### Get notified on Monitors changes

It is possible to register listeners to be invoked in case the number of connected monitors or their 
properties change.

|                           Listeners methods:                           |
|:----------------------------------------------------------------------:|
|       [plugListenerRegister](docs/docstrings.md#pluglistenerregister)       |
|     [changeListenerRegister](docs/docstrings.md#changelistenerregister)     |
|     [plugListenerUnregister](docs/docstrings.md#pluglistenerunregister)     |
|   [changeListenerUnregister](docs/docstrings.md#changelistenerunregister)   |
|   [isPlugListenerRegistered](docs/docstrings.md#ispluglistenerregistered)   |
| [isChangeListenerRegistered](docs/docstrings.md#ischangelistenerregistered) |

The information passed to the listeners is as follows:

   - Names of the monitors which have changed (as a list of strings)
   - All monitors info, as returned by `getAllMonitorsDict()`. To access monitors properties, use monitor name/s as dictionary key

Example:

```python
import pymonctl as pmc
import time

def countChanged(names, screensInfo):
    print("MONITOR PLUGGED/UNPLUGGED:", names)
    for name in names:
        print("MONITORS INFO:", screensInfo[name])

def propsChanged(names, screensInfo):
    print("MONITOR CHANGED:", names)
    for name in names:
        print("MONITORS INFO:", screensInfo[name])

pmc.plugListenerRegister(countChanged)
pmc.changeListenerRegister(propsChanged)

print("Plug/Unplug monitors, or change monitor properties while running")
print("Press Ctl-C to Quit")
while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

pmc.plugListenerUnregister(countChanged)
pmc.changeListenerUnregister(propsChanged)
```

---

## Install <a name="install"></a>

To install this module on your system, you can use pip:

    python -m pip install pymonctl

or using uv:

    uv add pymonctl

Alternatively, you can download the wheel file (.whl) available in the [Download page](https://pypi.org/project/PyMonCtl/#files) and the [dist folder](https://github.com/Kalmat/PyMonCtl/tree/master/dist), and run this (don't forget to replace 'x.x.xx' with proper version number):

    python -m pip install PyMonCtl-x.x.xx-py3-none-any.whl

You may want to add `--force-reinstall` option to be sure you are installing the right dependencies version.

Then, you can use it on your own projects just importing it:

    import pymonctl

### Additional tools/extensions/APIs used:

#### Linux:
* Xlib's randr extension
* xrandr command-line tool
* xset command-line tool

#### Windows:
* VCP MCCS API interface

#### macOS:
* pmset command-line tool

## Support <a name="support"></a>

In case you have a problem, comments or suggestions, do not hesitate to [open issues](https://github.com/Kalmat/PyMonCtl/issues) on the [project homepage](https://github.com/Kalmat/PyMonCtl)

## Using this code <a name="using"></a>

If you want to use this code or contribute, you can either:

* Create a fork of the [repository](https://github.com/Kalmat/PyMonCtl), or 
* [Download the repository](https://github.com/Kalmat/PyMonCtl/archive/refs/heads/master.zip), uncompress, and open it on your IDE of choice (e.g. PyCharm)

Be sure you install all dev dependencies by running:

    uv sync

or
    python -m venv .venv
    python -m pip install -e . --group=dev

## Test <a name="test"></a>

To test this module on your own system, cd to `tests` folder and run:

    uv run test_pymonctl.py
