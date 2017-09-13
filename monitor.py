from ctypes import windll
from ctypes import sizeof, byref, Structure, WinError
from ctypes import c_int, POINTER, WINFUNCTYPE
from ctypes.wintypes import (BOOL, DWORD, HANDLE, HDC, HMONITOR, LPARAM, RECT,
                             WCHAR)

__all__ = ['enum_display_monitors', 'get_physical_monitors',
           'destroy_physical_monitor', 'destroy_physical_monitors',
           'save_current_monitor_settings',
           'get_monitor_brightness', 'set_monitor_brightness',
           'get_monitor_contrast', 'set_monitor_contrast',
           'get_monitor_red_green_or_blue_gain',
           'set_monitor_red_green_or_blue_gain',
           'get_monitor_red_gain', 'set_monitor_red_gain',
           'get_monitor_green_gain', 'set_monitor_green_gain',
           'get_monitor_blue_gain', 'set_monitor_blue_gain',
           'get_monitor_red_green_and_blue_gain',
           'set_monitor_red_green_and_blue_gain',
           'get_monitor_red_green_or_blue_drive',
           'set_monitor_red_green_or_blue_drive',
           'get_monitor_red_drive', 'set_monitor_red_drive',
           'get_monitor_green_drive', 'set_monitor_green_drive',
           'get_monitor_blue_drive', 'set_monitor_blue_drive',
           'get_monitor_red_green_and_blue_drive',
           'set_monitor_red_green_and_blue_drive']

MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)
PHYSICAL_MONITOR_DESCRIPTION_SIZE = 128
MONITORINFOF_PRIMARY = 1

MC_RED_GAIN = c_int(0)
MC_GREEN_GAIN = c_int(1)
MC_BLUE_GAIN = c_int(2)
MC_GAIN_TYPE = [MC_RED_GAIN, MC_GREEN_GAIN, MC_BLUE_GAIN]

MC_RED_DRIVE = c_int(0)
MC_GREEN_DRIVE = c_int(1)
MC_BLUE_DRIVE = c_int(2)
MC_DRIVE_TYPE = [MC_RED_DRIVE, MC_GREEN_DRIVE, MC_BLUE_DRIVE]

EnumDisplayMonitors = windll.user32.EnumDisplayMonitors
GetMonitorInfo = windll.user32.GetMonitorInfoW
GetNumberOfPhysicalMonitorsFromHMONITOR = \
    windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR
GetPhysicalMonitorsFromHMONITOR = windll.dxva2.GetPhysicalMonitorsFromHMONITOR
DestroyPhysicalMonitor = windll.dxva2.DestroyPhysicalMonitor
SaveCurrentMonitorSettings = windll.dxva2.SaveCurrentMonitorSettings
GetMonitorBrightness = windll.dxva2.GetMonitorBrightness
SetMonitorBrightness = windll.dxva2.SetMonitorBrightness
GetMonitorContrast = windll.dxva2.GetMonitorContrast
SetMonitorContrast = windll.dxva2.SetMonitorContrast
GetMonitorRedGreenOrBlueGain = windll.dxva2.GetMonitorRedGreenOrBlueGain
SetMonitorRedGreenOrBlueGain = windll.dxva2.SetMonitorRedGreenOrBlueGain
GetMonitorRedGreenOrBlueDrive = windll.dxva2.GetMonitorRedGreenOrBlueDrive
SetMonitorRedGreenOrBlueDrive = windll.dxva2.SetMonitorRedGreenOrBlueDrive


class PHYSICAL_MONITOR(Structure):
    _fields_ = [('hPhysicalMonitor', HANDLE),
                ('szPhysicalMonitorDescription',
                 WCHAR * PHYSICAL_MONITOR_DESCRIPTION_SIZE)]


class MONITORINFO(Structure):
    _fields_ = [('cbSize', DWORD),
                ('rcMonitor', RECT),
                ('rcWork', RECT),
                ('dwFlags', DWORD)]


def enum_display_monitors():
    monitors = []

    def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        mi = MONITORINFO()
        mi.cbSize = sizeof(mi)

        if not GetMonitorInfo(hMonitor, byref(mi)):
            raise WinError()

        monitors.append((hMonitor, bool(mi.dwFlags & MONITORINFOF_PRIMARY)))
        return True

    if not EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), None):
        raise WinError()

    yield from monitors


def get_physical_monitors(monitor):
    count = DWORD()

    if not GetNumberOfPhysicalMonitorsFromHMONITOR(monitor, byref(count)):
        raise WinError()

    physicalMonitorArray = (PHYSICAL_MONITOR * count.value)()

    if not GetPhysicalMonitorsFromHMONITOR(monitor, count.value,
                                           physicalMonitorArray):
        raise WinError()

    physicalMonitors = []

    for physicalMonitor in physicalMonitorArray:
        physicalMonitors.append(physicalMonitor.hPhysicalMonitor)

    return physicalMonitors


def destroy_physical_monitor(monitor):
    if not DestroyPhysicalMonitor(monitor):
        raise WinError()


def destroy_physical_monitors(monitors):
    for monitor in monitors:
        destroy_physical_monitor(monitor)


def save_current_monitor_settings(monitor):
    if not SaveCurrentMonitorSettings(monitor):
        raise WinError()


def get_monitor_brightness(monitor):
    minimumBrightness = DWORD()
    currentBrightness = DWORD()
    maximumBrightness = DWORD()

    if not GetMonitorBrightness(monitor,
                                byref(minimumBrightness),
                                byref(currentBrightness),
                                byref(maximumBrightness)):
        raise WinError()

    return (minimumBrightness.value,
            currentBrightness.value,
            maximumBrightness.value)


def set_monitor_brightness(monitor, brightness):
    if not SetMonitorBrightness(monitor, DWORD(brightness)):
        raise WinError()


def get_monitor_contrast(monitor):
    minimumContrast = DWORD()
    currentContrast = DWORD()
    maximumContrast = DWORD()

    if not GetMonitorContrast(monitor,
                              byref(minimumContrast),
                              byref(currentContrast),
                              byref(maximumContrast)):
        raise WinError()

    return (minimumContrast.value,
            currentContrast.value,
            maximumContrast.value)


def set_monitor_contrast(monitor, brightness):
    if not SetMonitorContrast(monitor, DWORD(brightness)):
        raise WinError()


def get_monitor_red_green_or_blue_gain(monitor, type):
    minimumGain = DWORD()
    currentGain = DWORD()
    maximumGain = DWORD()

    if not GetMonitorRedGreenOrBlueGain(monitor,
                                        MC_GAIN_TYPE[type],
                                        byref(minimumGain),
                                        byref(currentGain),
                                        byref(maximumGain)):
        raise WinError()

    return (minimumGain.value,
            currentGain.value,
            maximumGain.value)


def set_monitor_red_green_or_blue_gain(monitor, type, gain):
    if not SetMonitorRedGreenOrBlueGain(monitor, MC_GAIN_TYPE[type],
                                        DWORD(gain)):
        raise WinError()


def get_monitor_red_gain(monitor):
    return get_monitor_red_green_or_blue_gain(monitor, 0)


def set_monitor_red_gain(monitor, gain):
    set_monitor_red_green_or_blue_gain(monitor, 0, gain)


def get_monitor_green_gain(monitor):
    return get_monitor_red_green_or_blue_gain(monitor, 1)


def set_monitor_green_gain(monitor, gain):
    set_monitor_red_green_or_blue_gain(monitor, 1, gain)


def get_monitor_blue_gain(monitor):
    return get_monitor_red_green_or_blue_gain(monitor, 2)


def set_monitor_blue_gain(monitor, gain):
    set_monitor_red_green_or_blue_gain(monitor, 2, gain)


def get_monitor_red_green_and_blue_gain(monitor):
    return (get_monitor_red_gain(monitor),
            get_monitor_green_gain(monitor),
            get_monitor_blue_gain(monitor))


def set_monitor_red_green_and_blue_gain(monitor, gainRed, gainGreen, gainBlue):
    set_monitor_red_gain(monitor, gainRed)
    set_monitor_green_gain(monitor, gainGreen)
    set_monitor_blue_gain(monitor, gainBlue)


def get_monitor_red_green_or_blue_drive(monitor, type):
    minimumDrive = DWORD()
    currentDrive = DWORD()
    maximumDrive = DWORD()

    if not GetMonitorRedGreenOrBlueDrive(monitor,
                                         MC_DRIVE_TYPE[type],
                                         byref(minimumDrive),
                                         byref(currentDrive),
                                         byref(maximumDrive)):
        raise WinError()

    return (minimumDrive.value,
            currentDrive.value,
            maximumDrive.value)


def set_monitor_red_green_or_blue_drive(monitor, type, drive):
    if not SetMonitorRedGreenOrBlueDrive(monitor, MC_DRIVE_TYPE[type],
                                         DWORD(drive)):
        raise WinError()


def get_monitor_red_drive(monitor):
    return get_monitor_red_green_or_blue_drive(monitor, 0)


def set_monitor_red_drive(monitor, drive):
    set_monitor_red_green_or_blue_drive(monitor, 0, drive)


def get_monitor_green_drive(monitor):
    return get_monitor_red_green_or_blue_drive(monitor, 1)


def set_monitor_green_drive(monitor, drive):
    set_monitor_red_green_or_blue_drive(monitor, 1, drive)


def get_monitor_blue_drive(monitor):
    return get_monitor_red_green_or_blue_drive(monitor, 2)


def set_monitor_blue_drive(monitor, drive):
    set_monitor_red_green_or_blue_drive(monitor, 2, drive)


def get_monitor_red_green_and_blue_drive(monitor):
    return (get_monitor_red_drive(monitor),
            get_monitor_green_drive(monitor),
            get_monitor_blue_drive(monitor))


def set_monitor_red_green_and_blue_drive(monitor, driveRed, driveGreen,
                                         driveBlue):
    set_monitor_red_drive(monitor, driveRed)
    set_monitor_green_drive(monitor, driveGreen)
    set_monitor_blue_drive(monitor, driveBlue)
