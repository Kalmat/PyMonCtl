## General Functions

<a id="pymonctl._main.getAllMonitors"></a>

#### getAllMonitors

```python
def getAllMonitors() -> list[Monitor]
```

Get the list with all Monitor instances from plugged monitors.

In case you plan to use this function in a scenario in which it could be invoked quickly and repeatedly,
it's highly recommended to enable update watchdog (see enableUpdate() function).

**Returns**:

list of Monitor instances

<a id="pymonctl._main.getAllMonitorsDict"></a>

#### getAllMonitorsDict

```python
def getAllMonitorsDict() -> dict[str, ScreenValue]
```

Get all monitors info plugged to the system, as a dict.

In case you plan to use this function in a scenario in which it could be invoked quickly and repeatedly,
it's highly recommended to enable update watchdog (see enableUpdate() function).

**Returns**:

Monitors info as python dictionary
Output Format:
    Key:
        Display name (in macOS it is necessary to add handle to avoid duplicates)

    Values:
        "system_name":
            display name as returned by the system (in macOS, the name can be duplicated!)
        "id":
            display handle according to each platform/OS
        "is_primary":
            ''True'' if monitor is primary (shows clock and notification area, sign in, lock, CTRL+ALT+DELETE screens...)
        "position":
            Point(x, y) struct containing the display position ((0, 0) for the primary screen)
        "size":
            Size(width, height) struct containing the display size, in pixels
        "workarea":
            Rect(left, top, right, bottom) struct with the screen workarea, in pixels
        "scale":
            Scale ratio, as a tuple of (x, y) scale percentage
        "dpi":
            Dots per inch, as a tuple of (x, y) dpi values
        "orientation":
            Display orientation: 0 - Landscape / 1 - Portrait / 2 - Landscape (reversed) / 3 - Portrait (reversed)
        "frequency":
            Refresh rate of the display, in Hz
        "colordepth":
            Bits per pixel referred to the display color depth

<a id="pymonctl._main.getMonitorsCount"></a>

#### getMonitorsCount

```python
def getMonitorsCount() -> int
```

Get the number of monitors currently connected to the system.

**Returns**:

number of monitors as integer

<a id="pymonctl._main.getPrimary"></a>

#### getPrimary

```python
def getPrimary() -> Monitor
```

Get primary monitor instance. This is equivalent to invoking ''Monitor()'', with empty input params.

**Returns**:

Monitor instance or None

<a id="pymonctl._main.findMonitorsAtPoint"></a>

#### findMonitorsAtPoint

```python
def findMonitorsAtPoint(x: int, y: int) -> List[Monitor]
```

Get all Monitor class instances in which given coordinates (x, y) are found.

**Arguments**:

- `x`: target X coordinate
- `y`: target Y coordinate

**Returns**:

List of Monitor instances or empty

<a id="pymonctl._main.findMonitorsAtPointInfo"></a>

#### findMonitorsAtPointInfo

```python
def findMonitorsAtPointInfo(x: int, y: int) -> List[dict[str, ScreenValue]]
```

Get all monitors info in which given coordinates (x, y) are found.

**Arguments**:

- `x`: target X coordinate
- `y`: target Y coordinate

**Returns**:

list of monitor info (see getAllMonitorsDict() doc) as a list of dicts, or empty

<a id="pymonctl._main.findMonitorWithName"></a>

#### findMonitorWithName

```python
def findMonitorWithName(name: str) -> Optional[Monitor]
```

Get the Monitor class instance which name matches given name.

**Arguments**:

- `name`: target monitor name

**Returns**:

Monitor or None if not found

<a id="pymonctl._main.findMonitorWithNameInfo"></a>

#### findMonitorWithNameInfo

```python
def findMonitorWithNameInfo(name: str) -> dict[str, ScreenValue]
```

Get monitor instance which name matches given name.

**Arguments**:

- `name`: target monitor name

**Returns**:

monitor info (see getAllMonitorsDict() doc) as dict, or empty

<a id="pymonctl._main.arrangeMonitors"></a>

#### arrangeMonitors

```python
def arrangeMonitors(arrangement: dict[str,
                                      dict[str,
                                           Optional[Union[str, int, Position,
                                                          Point, Size]]]])
```

Arrange all monitors in a given shape.

For that, you must pass a dict with the following structure:
    "Monitor name":
        monitor name as keys() returned by getAllMonitorsDict() (don't use "system_name" value for this)
            "relativePos":
                position of this monitor in relation to the monitor provided in ''relativeTo''
            "relativeTo":
                monitor name to which ''relativePos'' is referred to (or None if PRIMARY)


You MUST pass the position of ALL monitors, and SET ONE of them as PRIMARY.

HIGHLY RECOMMENDED: When building complex arrangements, start by the primary monitor and then build the rest
taking previous ones as references.

EXAMPLE for a 3-Monitors setup in which second is at the left and third is on top of primary monitor:

    {
        "Display_1": {"relativePos": Position.PRIMARY, "relativeTo": None},

        "Display_2": {"relativePos": Position.LEFT_TOP, "relativeTo": "Display_1"},

        "Display_3": {"relativePos": Position.ABOVE_LEFT, "relativeTo": "Display_1"}
    }

**Arguments**:

- `arrangement`: arrangement structure as dict

<a id="pymonctl._main.getMousePos"></a>

#### getMousePos

```python
def getMousePos() -> Point
```

Get the current (x, y) coordinates of the mouse pointer on screen, in pixels

**Returns**:

Point struct

<a id="pymonctl._main.saveSetup"></a>

#### saveSetup

```python
def saveSetup() -> List[Tuple[Monitor, ScreenValue]]
```

Save current monitors setup information to be restored afterward.

If you just need monitors information in dictionary format, use getAllMonitorsDict() instead.

If you need all monitors instances to access all methods, use getAllMonitors() instead.

**Returns**:

list of tuples containing all necessary info to restore saved setup as required by restoreSetup()

<a id="pymonctl._main.restoreSetup"></a>

#### restoreSetup

```python
def restoreSetup(setup: List[Tuple[Monitor, ScreenValue]])
```

Restore given monitors setup (position, mode, orientation, scale, etc.). The function will also

try to re-attach / turn on / wake monitors if needed.

In case you want to just reposition monitors without changing all other settings, use arrangeMonitors() instead.

**Arguments**:

- `setup`: monitors info dictionary as returned by saveSetup()

<a id="pymonctl._main.BaseMonitor"></a>

<a id="pymonctl.version"></a>

#### version

```python
def version(numberOnly: bool = True) -> str
```

Returns the current version of PyMonCtl module, in the form ''x.x.xx'' as string

## Monitor Class Methods

```python
class Monitor()
```

<a id="pymonctl._main.BaseMonitor.size"></a>

#### size

```python
@property
@abstractmethod
def size() -> Optional[Size]
```

Get the dimensions of the monitor as a size struct (width, height)

This property can not be set independently. To do so, choose an allowed mode (from monitor.allModes)
and set the monitor mode property (monitor.mode = selectedMode)

**Returns**:

Size

<a id="pymonctl._main.BaseMonitor.workarea"></a>

#### workarea

```python
@property
@abstractmethod
def workarea() -> Optional[Rect]
```

Get dimensions of the "usable by applications" area (screen size minus docks, taskbars and so on), as

a rect struct (x, y, right, bottom)

This property can not be set.

**Returns**:

Rect

<a id="pymonctl._main.BaseMonitor.position"></a>

#### position

```python
@property
@abstractmethod
def position() -> Optional[Point]
```

Get monitor position coordinates as a point struct (x, y)

This property can not be set. Use setPosition() method instead.

**Returns**:

Point

<a id="pymonctl._main.BaseMonitor.setPosition"></a>

#### setPosition

```python
@abstractmethod
def setPosition(relativePos: Union[int, Position, Point, Tuple[int, int]],
                relativeTo: Optional[str])
```

Change relative position of the current the monitor in relation to another existing monitor (e.g. primary monitor).

On Windows and macOS, setting position to (0, 0) will also mean setting the monitor as primary, and viceversa;
but not on Linux (on Linux, combine setPrimary() and setPosition() to get desired config).

In general, it is HIGHLY recommendable to use arrangeMonitors() method instead of setPosition(), and most
especially in complex arrangements or setups with more than 2 monitors.

Important OS-dependent behaviors and limitations:

- On Windows, primary monitor is mandatory, and it is always placed at (0, 0) coordinates. Besides, the monitors can not overlap. To set a monitor as Primary, it is necessary to reposition primary monitor first, so the rest of monitors will sequentially be repositioned to LEFT.

- On Linux, primary monitor can be anywhere, and even there can be no primary monitor. Monitors can overlap, so take this into account when setting a new monitor position. Also bear in mind that xranr won't accept negative values, so the whole config will be referenced to (0, 0) coordinates.

- On macOS, primary monitor is mandatory, and it is always placed at (0, 0) coordinates. The monitors can overlap. To set a monitor as Primary, it is necessary to reposition primary monitor first, so the rest of monitors will sequentially be repositioned to LEFT.

**Arguments**:

- `relativePos`: position in relation to another existing monitor (e.g. primary) as per Positions.*
- `relativeTo`: monitor in relation to which this monitor must be placed

<a id="pymonctl._main.BaseMonitor.box"></a>

#### box

```python
@property
@abstractmethod
def box() -> Optional[Box]
```

Get monitor dimensions as a box struct (x, y, width, height)

This property can not be set.

**Returns**:

Box

<a id="pymonctl._main.BaseMonitor.rect"></a>

#### rect

```python
@property
@abstractmethod
def rect() -> Optional[Rect]
```

Get monitor dimensions as a rect struct (x, y, right, bottom)

This property can not be set.

**Returns**:

Rect

<a id="pymonctl._main.BaseMonitor.scale"></a>

#### scale

```python
@property
@abstractmethod
def scale() -> Optional[Tuple[float, float]]
```

Get scale for the monitor

Note not all scales will be allowed for all monitors and/or modes

**Returns**:

tuple of float scale value in X, Y coordinates

<a id="pymonctl._main.BaseMonitor.setScale"></a>

#### setScale

```python
@abstractmethod
def setScale(scale: Tuple[float, float], applyGlobally: bool = True)
```

Change scale for the monitor

Note not all scales will be allowed for all monitors and/or modes

**Arguments**:

- `scale`: target percentage as tuple of float value
- `applyGlobally`: (GNOME/X11 ONLY) Will affect all monitors (''True'', default) or selected one only (''False'')

<a id="pymonctl._main.BaseMonitor.dpi"></a>

#### dpi

```python
@property
@abstractmethod
def dpi() -> Optional[Tuple[float, float]]
```

Get the dpi (dots/pixels per inch) value for the monitor

This property can not be set

**Returns**:

tuple of dpi float value in X, Y coordinates

<a id="pymonctl._main.BaseMonitor.orientation"></a>

#### orientation

```python
@property
@abstractmethod
def orientation() -> Optional[Union[int, Orientation]]
```

Get current orientation for the monitor identified by name (or primary if empty)

The available orientations are:
    0 - 0 degrees (normal)
    1 - 90 degrees (right)
    2 - 180 degrees (inverted)
    3 - 270 degrees (left)

**Returns**:

current orientation value as int (or Orientation value)

<a id="pymonctl._main.BaseMonitor.setOrientation"></a>

#### setOrientation

```python
@abstractmethod
def setOrientation(orientation: Optional[Union[int, Orientation]])
```

Change orientation for the monitor identified by name (or primary if empty)

The available orientations are:
    0 - 0 degrees (normal)
    1 - 90 degrees (right)
    2 - 180 degrees (inverted)
    3 - 270 degrees (left)

**Arguments**:

- `orientation`: orientation as per Orientations.*

<a id="pymonctl._main.BaseMonitor.frequency"></a>

#### frequency

```python
@property
@abstractmethod
def frequency() -> Optional[float]
```

Get current refresh rate of monitor.

This property can not be set independently. To do so, choose an allowed mode (from monitor.allModes)
and set the monitor mode property (monitor.mode = selectedMode)

**Returns**:

float

<a id="pymonctl._main.BaseMonitor.colordepth"></a>

#### colordepth

```python
@property
@abstractmethod
def colordepth() -> Optional[int]
```

Get the colordepth (bits per pixel to describe color) value for the monitor

This property can not be set

**Returns**:

int

<a id="pymonctl._main.BaseMonitor.brightness"></a>

#### brightness

```python
@property
@abstractmethod
def brightness() -> Optional[int]
```

Get the brightness of monitor. The return value is normalized to 0-100 (as a percentage)

**Returns**:

brightness as int (1-100)

<a id="pymonctl._main.BaseMonitor.setBrightness"></a>

#### setBrightness

```python
@abstractmethod
def setBrightness(brightness: Optional[int])
```

Change the brightness of monitor. The input parameter must be defined as a percentage (0-100)

**Arguments**:

- `brightness`: brightness value to be set (0-100)

<a id="pymonctl._main.BaseMonitor.contrast"></a>

#### contrast

```python
@property
@abstractmethod
def contrast() -> Optional[int]
```

Get the contrast of monitor. The return value is normalized to 0-100 (as a percentage)

WARNING: In Linux and macOS contrast is calculated from Gamma RGB values.

**Returns**:

contrast as int (1-100)

<a id="pymonctl._main.BaseMonitor.setContrast"></a>

#### setContrast

```python
@abstractmethod
def setContrast(contrast: Optional[int])
```

Change the contrast of monitor. The input parameter must be defined as a percentage (0-100)

WARNING: In Linux and macOS the change will apply to Gamma homogeneously for all color components (R, G, B).

Example for Linux: A value of 50.0 (50%), will result in a Gamma of ''0.5:0.5:0.5''

**Arguments**:

- `contrast`: contrast value to be set (0-100)

<a id="pymonctl._main.BaseMonitor.mode"></a>

#### mode

```python
@property
@abstractmethod
def mode() -> Optional[DisplayMode]
```

Get the current monitor mode (width, height, refresh-rate) for the monitor

**Returns**:

current mode as DisplayMode struct

<a id="pymonctl._main.BaseMonitor.setMode"></a>

#### setMode

```python
@abstractmethod
def setMode(mode: Optional[DisplayMode])
```

Change current monitor mode (resolution and/or refresh-rate) for the monitor

The mode must be one of the allowed modes by the monitor (see allModes property).

**Arguments**:

- `mode`: target mode as DisplayMode (width, height and frequency)

<a id="pymonctl._main.BaseMonitor.defaultMode"></a>

#### defaultMode

```python
@property
@abstractmethod
def defaultMode() -> Optional[DisplayMode]
```

Get the preferred mode for the monitor

**Returns**:

DisplayMode struct (width, height, frequency)

<a id="pymonctl._main.BaseMonitor.setDefaultMode"></a>

#### setDefaultMode

```python
@abstractmethod
def setDefaultMode()
```

Change current mode to default / preferred mode

<a id="pymonctl._main.BaseMonitor.allModes"></a>

#### allModes

```python
@property
@abstractmethod
def allModes() -> list[DisplayMode]
```

Get all allowed modes for the monitor

**Returns**:

list of DisplayMode (width, height, frequency)

<a id="pymonctl._main.BaseMonitor.isPrimary"></a>

#### isPrimary

```python
@property
@abstractmethod
def isPrimary() -> bool
```

Check if given monitor is primary.

**Returns**:

''True'' if given monitor is primary, ''False'' otherwise

<a id="pymonctl._main.BaseMonitor.setPrimary"></a>

#### setPrimary

```python
@abstractmethod
def setPrimary()
```

Set monitor as the primary one.

WARNING: Notice this can also change the monitor position, altering the whole monitors setup.
To properly handle this, use arrangeMonitors() instead.

<a id="pymonctl._main.BaseMonitor.turnOn"></a>

#### turnOn

```python
@abstractmethod
def turnOn()
```

Turn on or wakeup monitor if it was off or suspended (but not if it is detached).

<a id="pymonctl._main.BaseMonitor.turnOff"></a>

#### turnOff

```python
@abstractmethod
def turnOff()
```

Turn off monitor

WARNING:

    Windows:
        If monitor has no VCP MCCS support, it can not be addressed separately, so ALL monitors will be turned off.
        To address a specific monitor, try using detach() method

    macOS:
        Didn't find a way to programmatically turn off a given monitor. Use suspend instead.

<a id="pymonctl._main.BaseMonitor.isOn"></a>

#### isOn

```python
@property
@abstractmethod
def isOn() -> Optional[bool]
```

Check if monitor is on

WARNING: not working in macOS (... yet?)

**Returns**:

''True'' if monitor is on

<a id="pymonctl._main.BaseMonitor.suspend"></a>

#### suspend

```python
@abstractmethod
def suspend()
```

Suspend (standby) monitor

WARNING:

    Windows:
        If monitor has no VCP MCCS support, it can not be addressed separately, so ALL monitors will be suspended.
        To address a specific monitor, try using detach() method

    Linux:
        This method will suspend ALL monitors.

    macOS:
        This method will suspend ALL monitors.

<a id="pymonctl._main.BaseMonitor.isSuspended"></a>

#### isSuspended

```python
@property
@abstractmethod
def isSuspended() -> Optional[bool]
```

Check if monitor is in standby mode

**Returns**:

''True'' if monitor is in standby mode

<a id="pymonctl._main.BaseMonitor.attach"></a>

#### attach

```python
@abstractmethod
def attach()
```

Attach a previously detached monitor to system

WARNING: In Windows, all IDs may change when attach / detach / plug / unplug a monitor. The module
         will try to refresh all IDs from all Monitor class instances... but take into account it may fail!

WARNING: not working in macOS (... yet?)

<a id="pymonctl._main.BaseMonitor.detach"></a>

#### detach

```python
@abstractmethod
def detach(permanent: bool = False)
```

Detach monitor from system.

Be aware that if you detach a monitor and the script ends, you will have to physically re-attach the monitor.

It will not likely work if system has just one monitor plugged.

WARNING: In Windows, all IDs may change when attach / detach / plug / unplug a monitor. The module
         will try to refresh all IDs from all Monitor class instances... but take into account it may fail!

WARNING: not working in macOS (... yet?)

**Arguments**:

- `permanent`: set to ''True'' to permanently detach the monitor from system

<a id="pymonctl._main.BaseMonitor.isAttached"></a>

#### isAttached

```python
@property
@abstractmethod
def isAttached() -> Optional[bool]
```

Check if monitor is attached (not necessarily ON) to system

**Returns**:

''True'' if monitor is attached

<a id="pymonctl._main._UpdateScreens"></a>

## Watchdog Methods

```python
class _UpdateScreens(threading.Thread)
```

<a id="pymonctl._main.enableUpdateInfo"></a>

#### enableUpdateInfo

```python
def enableUpdateInfo()
```

Enable this only if you need to keep track of monitor-related events like changing its resolution, position,
or if monitors can be dynamically plugged or unplugged in a multi-monitor setup. This function can also be
useful in scenarios in which monitors list or properties need to be queried quickly and repeatedly, thus keeping
this information updated without impacting main process.

If enabled, it will activate a separate thread which will periodically update the list of monitors and
their properties (see getAllMonitors() and getAllMonitorsDict() functions).

If disabled, the information on the monitors connected to the system will be updated right at the moment,
but this might be slow and CPU-consuming, especially if quickly and repeatedly invoked.

<a id="pymonctl._main.disableUpdateInfo"></a>

#### disableUpdateInfo

```python
def disableUpdateInfo()
```

The monitors information will be immediately queried after disabling this feature, not taking advantage of
keeping information updated on a separate thread.

Enable this process again, or invoke getMonitors() function if you need updated info.

<a id="pymonctl._main.plugListenerRegister"></a>

#### plugListenerRegister

```python
def plugListenerRegister(
        monitorCountChanged: Callable[[List[str], dict[str, ScreenValue]],
                                      None])
```

Use this only if you need to keep track of monitor that can be dynamically plugged or unplugged in a

multi-monitor setup.

The registered callbacks will be invoked in case the number of connected monitors change.
The information passed to the callbacks is:

    - Names of the screens which have changed (as a list of strings).
    - All screens info, as returned by getAllMonitorsDict() function.

It is possible to access all monitors information by using screen name as dictionary key

**Arguments**:

- `monitorCountChanged`: callback to be invoked in case the number of monitor connected changes

<a id="pymonctl._main.plugListenerUnregister"></a>

#### plugListenerUnregister

```python
def plugListenerUnregister(
        monitorCountChanged: Callable[[List[str], dict[str, ScreenValue]],
                                      None])
```

Use this function to un-register your custom callback. The callback will not be invoked anymore in case

the number of monitor changes.

**Arguments**:

- `monitorCountChanged`: callback previously registered

<a id="pymonctl._main.changeListenerRegister"></a>

#### changeListenerRegister

```python
def changeListenerRegister(
        monitorPropsChanged: Callable[[List[str], dict[str, ScreenValue]],
                                      None])
```

Use this only if you need to keep track of monitor properties changes (position, size, refresh-rate, etc.) in a

multi-monitor setup.

The registered callbacks will be invoked in case these properties change.
The information passed to the callbacks is:

    - Names of the screens which have changed (as a list of strings).
    - All screens info, as returned by getAllMonitorsDict() function.

It is possible to access all monitor information by using screen name as dictionary key

**Arguments**:

- `monitorPropsChanged`: callback to be invoked in case the number of monitor properties change

<a id="pymonctl._main.changeListenerUnregister"></a>

#### changeListenerUnregister

```python
def changeListenerUnregister(
        monitorPropsChanged: Callable[[List[str], dict[str, ScreenValue]],
                                      None])
```

Use this function to un-register your custom callback. The callback will not be invoked anymore in case

the monitor properties change.

**Arguments**:

- `monitorPropsChanged`: callback previously registered

<a id="pymonctl._main.isWatchdogEnabled"></a>

#### isWatchdogEnabled

```python
def isWatchdogEnabled() -> bool
```

Check if the daemon updating screens information and (if applies) invoking callbacks when needed is alive.

If it is not, just enable update process, or register the callbacks you need. It will be automatically started.

**Returns**:

Return ''True'' is process (thread) is alive

<a id="pymonctl._main.isUpdateInfoEnabled"></a>

#### isUpdateInfoEnabled

```python
def isUpdateInfoEnabled() -> bool
```

Get monitors watch process status (enabled / disabled).

**Returns**:

Returns ''True'' if enabled.

<a id="pymonctl._main.isPlugListenerRegistered"></a>

#### isPlugListenerRegistered

```python
def isPlugListenerRegistered(
        monitorCountChanged: Callable[[List[str], dict[str, ScreenValue]],
                                      None])
```

Check if callback is already registered to be invoked when monitor plugged count change

**Returns**:

Returns ''True'' if registered

<a id="pymonctl._main.isChangeListenerRegistered"></a>

#### isChangeListenerRegistered

```python
def isChangeListenerRegistered(
        monitorPropsChanged: Callable[[List[str], dict[str, ScreenValue]],
                                      None])
```

Check if callback is already registered to be invoked when monitor properties change

**Returns**:

Returns ''True'' if registered

<a id="pymonctl._main.updateWatchdogInterval"></a>

#### updateWatchdogInterval

```python
def updateWatchdogInterval(interval: float)
```

Change the wait interval for the thread loop in seconds (or fractions), Default is 0.50 seconds.

Higher values will take longer to detect and notify changes.

Lower values will make it faster, but will consume more CPU.

Also bear in mind that the OS will take some time to refresh changes, so lowering the update interval
may not necessarily produce better (faster) results.

**Arguments**:

- `interval`: new interval value in seconds (or fractions), as float.

## Structs

<a id="pymonctl._structs.Box"></a>

#### Box

```python
class Box(NamedTuple)
```

Container class to handle Box struct (left, top, width, height)

<a id="pymonctl._structs.Rect"></a>

#### Rect

```python
class Rect(NamedTuple)
```

Container class to handle Rect struct (left, top, right, bottom)

<a id="pymonctl._structs.Point"></a>

#### Point

```python
class Point(NamedTuple)
```

Container class to handle Point struct (x, y)

<a id="pymonctl._structs.Size"></a>

#### Size

```python
class Size(NamedTuple)
```

Container class to handle Size struct (right, bottom)

<a id="pymonctl._structs.ScreenValue"></a>

#### ScreenValue

```python
class ScreenValue(TypedDict)
```

Container class to handle ScreenValue struct:

    - system_name (str): name of the monitor as known by the system
    - id (int): handle/identifier of the monitor
    - is_primary (bool): ''True'' if it is the primary monitor
    - position (Point): position of the monitor
    - size (Size): size of the monitor, in pixels
    - workarea (Rect): coordinates of the usable area of the monitor usable by apps/windows (no docks, taskbars, ...)
    - scale (Tuple[int, int]): text scale currently applied to monitor
    - dpi (Tuple[int, int]): dpi values of current resolution
    - orientation (int): rotation value of the monitor as per Orientation values (NORMAL = 0,  RIGHT = 1,  INVERTED = 2, LEFT = 3)
    - frequency (float): refresh rate of the monitor
    - colordepth (int): color depth of the monitor

<a id="pymonctl._structs.DisplayMode"></a>

#### DisplayMode

```python
class DisplayMode(NamedTuple)
```

Container class to handle DisplayMode struct:

    - width (int): width, in pixels
    - height (int): height, in pixels
    - frequency (float): refresh rate
