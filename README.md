# PyMonCtl
[![Type Checking](https://github.com/Kalmat/PyMonCtl/actions/workflows/type-checking.yml/badge.svg)](https://github.com/Kalmat/PyMonCtl/actions/workflows/type-checking.yml)
[![PyPI version](https://badge.fury.io/py/PyMonCtl.svg)](https://badge.fury.io/py/PyMonCtl)

Cross-Platform module which provides a set of features to get info on and control monitors.

Additional tools/extensions/APIs used:
- Linux:
  - Xlib's randr extension
  - xrandr command-line tool
  - xset command-line tool
- Windows:
  - VCP MCCS API interface
- macOS:
  - pmset command-line tool
    

## General Features

Functions to get monitor instances, get info and arrange monitors plugged to the system.

|   General functions:    |
|:-----------------------:|
|     getAllMonitors      |
|   getAllMonitorsDict    |
|    getMonitorsCount     |
|       getPrimary        |
|   findMonitorsAtPoint   |
| findMonitorsAtPointInfo |
|   findMonitorWithName   |
| findMonitorWithNameInfo |
|        saveSetup        |
|      restoreSetup       |
|     arrangeMonitors     |
|       getMousePos       |


## Monitor Class

Class to access all methods and functions to get info and control a given monitor plugged to the system.

This class is not meant to be directly instantiated. Instead, use convenience functions like `getAllMonitors()`,
`getPrimary()` or `findMonitorsAtPoint(x, y)`. Use [PyWinCtl](https://github.com/Kalmat/PyWinCtl) module in case you need to 
find the monitor a given window is in, by using `getMonitor()` method which returns the name of the monitor that
can directly be used to invoke `findMonitorWithName(name)` function.

To instantiate it, you need to pass the monitor handle (OS-dependent). It can raise ValueError exception in case 
the provided handle is not valid.

|    Methods     | Windows | Linux | macOS |
|:--------------:|:-------:|:-----:|:-----:|
|      size      |    X    |   X   |   X   |
|    workarea    |    X    |   X   |   X   |
|    position    |    X    |   X   |   X   |
|  setPosition   |    X    |   X   |   X   |
|      box       |    X    |   X   |   X   |
|      rect      |    X    |   X   |   X   |
|   frequency    |    X    |   X   |   X   |
|   colordepth   |    X    |   X   |   X   |
|      dpi       |    X    |   X   |   X   |
|     scale      |    X    |   X   |   X   |
|    setScale    |    X    |   X   |   X   |
|  orientation   |    X    |   X   |   X   |
| setOrientation |    X    |   X   | X (1) |
|   brightness   |  X (2)  |   X   | X (1) |
| setBrightness  |  X (2)  |   X   | X (1) |
|    contrast    |  X (2)  | X (3) | X (3) |
|  setContrast   |  X (2)  | X (3) | X (3) |
|      mode      |    X    |   X   |   X   |
|    setMode     |    X    |   X   |   X   |
|  defaultMode   |    X    |   X   |   X   |
| setDefaultMode |    X    |   X   |   X   |
|    allModes    |    X    |   X   |   X   |
|   setPrimary   |    X    |   X   |   X   |
|   isPrimary    |    X    |   X   |   X   |
|     turnOn     |  X (4)  |   X   | X (4) |
|    turnOff     |  X (4)  |   X   | X (4) |
|      isOn      |  X (2)  |   X   |   X   |
|    suspend     |  X (4)  | X (4) | X (4) |
|  isSuspended   |  X (2)  |   X   |   X   |
|     attach     |    X    |   X   |       |
|     detach     |    X    |   X   |       |
|   isAttached   |    X    |   X   |   X   |


(1) Maybe not working in all macOS versions and/or architectures (thanks to University of [Utah - Marriott Library - Apple Infrastructure](https://github.com/univ-of-utah-marriott-library-apple/privacy_services_manager), [eryksun](https://stackoverflow.com/questions/22841741/calling-functions-with-arguments-from-corefoundation-using-ctypes) and [nriley](https://github.com/nriley/brightness/blob/master/brightness.c) for pointing me to the solution)

(2) If monitor has no VCP MCCS support, these methods won't likely work.

(3) It doesn't exactly return / change contrast, but gamma values.

(4) Different behaviour according to OS:
- Windows: Working with VCP MCCS support only.
- Linux: It will suspend ALL monitors. To address just one monitor, try using turnOff() / turnOn() / detach() / attach() methods.
- macOS: It will suspend ALL monitors. Use turnOn() to wake them up again


#### WARNING: Most of these properties may return ''None'' in case the value can not be obtained

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
      - xrandr will sort primary monitors first. Because of this and for homegeneity, when positioning a monitor as primary (only with setPosition() method), it will be placed at (0 ,0) and all the rest to RIGHT_TOP.
  - macOS:
      - Primary monitor is mandatory, and it is always placed at (0, 0) coordinates. 
      - Monitors can overlap, so take this into account when setting a new monitor position. 
      - To set a monitor as Primary, it is necessary to reposition primary monitor first, so the rest of monitors will sequentially be repositioned to RIGHT_TOP.
      - setScale() method uses a workaround by applying the nearest monitor mode to magnify text to given value

It is highly recommended to use `arrangeMonitors()` function for complex setups or just in case there are two or more monitors.   

## Keep track of Monitor(s) changes

You can activate a watchdog, running in a separate Thread, which will allow you to keep monitors 
information updated, without negatively impacting your main process, and define hooks and its callbacks to be  
notified when monitors are plugged / unplugged or their properties change.

|   Watchdog methods:    |
|:----------------------:|
|   isWatchdogEnabled    |
| updateWatchdogInterval |

The watchdog will automatically start while the update information is enabled and / or there are any listeners 
registered, and will automatically stop otherwise or if the script finishes.

You can check if the watchdog is working (`isWatchdogEnabled()`) and also change its update interval 
(`updateWatchdogInterval()`) in case you need a custom period (default is 0.5 seconds). Adjust this value to your needs, 
but take into account that higher values will take longer to detect and notify changes; whilst lower values will 
consume more CPU and may produce additional notifications for intermediate (non-final) status.

### Keep Monitors info updated

|    Info update methods:    |
|:--------------------------:|
|      enableUpdateInfo      |
|     disableUpdateInfo      |
|    isUpdateInfoEnabled     |

Enable this only if you need to keep track of monitor-related events like changing its resolution, position, scale,
or if monitors can be dynamically plugged or unplugged in a multi-monitor setup. If you need monitors info updated 
at a given moment, but not continuously updated, just invoke `getAllMonitors()` at your convenience.

If enabled, it will activate a separate thread which will periodically update the list of monitors and
their properties (see `getAllMonitors()` and `getAllMonitorsDict()` function).

### Get notified on Monitors changes

It is possible to register listeners to be invoked in case the number of connected monitors or their 
properties change.

|     Listeners methods:     |
|:--------------------------:|
|    plugListenerRegister    |
|   changeListenerRegister   |
|   plugListenerUnregister   |
|  changeListenerUnregister  |
|  isPlugListenerRegistered  |
| isChangeListenerRegistered |

The information passed to the listeners is as follows:

   - Names of the monitors which have changed (as a list of strings)
   - All monitors info, as returned by `getAllMonitorsDict()`. To access monitors properties, use monitor name/s as dictionary key

Example:

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


## INSTALL <a name="install"></a>

To install this module on your system, you can use pip: 

    pip install pymonctl

or

    python3 -m pip install pymonctl

Alternatively, you can download the wheel file (.whl) available in the [Download page](https://pypi.org/project/PyMonCtl/#files) and the [dist folder](https://github.com/Kalmat/PyMonCtl/tree/master/dist), and run this (don't forget to replace 'x.x.xx' with proper version number):

    pip install PyMonCtl-x.x.xx-py3-none-any.whl

You may want to add `--force-reinstall` option to be sure you are installing the right dependencies version.

Then, you can use it on your own projects just importing it:

    import pymonctl

## SUPPORT <a name="support"></a>

In case you have a problem, comments or suggestions, do not hesitate to [open issues](https://github.com/Kalmat/PyMonCtl/issues) on the [project homepage](https://github.com/Kalmat/PyMonCtl)

## USING THIS CODE <a name="using"></a>

If you want to use this code or contribute, you can either:

* Create a fork of the [repository](https://github.com/Kalmat/PyMonCtl), or 
* [Download the repository](https://github.com/Kalmat/PyMonCtl/archive/refs/heads/master.zip), uncompress, and open it on your IDE of choice (e.g. PyCharm)

Be sure you install all dependencies described on `requirements.txt` by using pip
    
    python3 -m pip install -r requirements.txt

## TEST <a name="test"></a>

To test this module on your own system, cd to `tests` folder and run:

    python3 test_pymonctl.py