from ctypes import windll
from ctypes import sizeof, byref, Structure, WinError
from ctypes import POINTER, WINFUNCTYPE
from ctypes.wintypes import (BOOL, DWORD, HANDLE, HDC, HMONITOR, HWND, LPARAM,
                             RECT, WCHAR, WORD)

__all__ = ['enum_display_monitors', 'get_physical_monitors',
           'destroy_physical_monitor', 'destroy_physical_monitors',
           'get_monitor_brightness', 'set_monitor_brightness',
           'get_monitor_contrast', 'set_monitor_contrast',
           'get_dc', 'release_dc', 'get_device_gamma_ramp',
           'set_device_gamma_ramp']

MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)
PHYSICAL_MONITOR_DESCRIPTION_SIZE = 128
MONITORINFOF_PRIMARY = 1

EnumDisplayMonitors = windll.user32.EnumDisplayMonitors
GetMonitorInfo = windll.user32.GetMonitorInfoW
GetDC = windll.user32.GetDC
ReleaseDC = windll.user32.ReleaseDC
GetNumberOfPhysicalMonitorsFromHMONITOR = \
    windll.dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR
GetPhysicalMonitorsFromHMONITOR = windll.dxva2.GetPhysicalMonitorsFromHMONITOR
DestroyPhysicalMonitor = windll.dxva2.DestroyPhysicalMonitor
GetMonitorBrightness = windll.dxva2.GetMonitorBrightness
SetMonitorBrightness = windll.dxva2.SetMonitorBrightness
GetMonitorContrast = windll.dxva2.GetMonitorContrast
SetMonitorContrast = windll.dxva2.SetMonitorContrast
GetDeviceGammaRamp = windll.gdi32.GetDeviceGammaRamp
SetDeviceGammaRamp = windll.gdi32.SetDeviceGammaRamp


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


def get_dc():
    hdc = GetDC(HWND(None))

    if not hdc:
        raise RuntimeError('GetDC(HWND(NULL)) returned NULL')

    return hdc


def release_dc(device):
    if not ReleaseDC(HWND(None), device):
        raise RuntimeError(
            'ReleaseDC(HWND(NULL), HDC({:#x})) returned 0'.format(device))


def get_device_gamma_ramp(device):
    ramp = (WORD * 256 * 3)()

    if not GetDeviceGammaRamp(device, byref(ramp)):
        raise WinError()

    return [[int(ramp[i][j]) for j in range(256)]
            for i in range(3)]


def set_device_gamma_ramp(device, ramp):
    _ramp = (WORD * 256 * 3)()

    for i in range(3):
        for j in range(256):
            _ramp[i][j] = WORD(ramp[i][j])

    if not SetDeviceGammaRamp(device, byref(_ramp)):
        raise WinError()
