from contextlib import contextmanager
from ctypes import byref, sizeof, Structure, windll, WinError
from ctypes import POINTER, WINFUNCTYPE
from ctypes.wintypes import (BOOL, DWORD, HANDLE, HDC, HMONITOR, LPARAM, RECT,
                             WCHAR, WORD)
from queue import Queue
from threading import Thread


__all__ = ['Context']

MONITORENUMPROC = WINFUNCTYPE(BOOL, HMONITOR, HDC, POINTER(RECT), LPARAM)
PHYSICAL_MONITOR_DESCRIPTION_SIZE = 128
MONITORINFOF_PRIMARY = 1

WORD_MAX = pow(2, sizeof(WORD) * 8) - 1

COLORMGMTCAPS = 121
CM_GAMMA_RAMP = 2

EnumDisplayMonitors = windll.user32.EnumDisplayMonitors
GetMonitorInfo = windll.user32.GetMonitorInfoW
GetDC = windll.user32.GetDC
ReleaseDC = windll.user32.ReleaseDC
GetDeviceCaps = windll.gdi32.GetDeviceCaps
GetDeviceGammaRamp = windll.gdi32.GetDeviceGammaRamp
SetDeviceGammaRamp = windll.gdi32.SetDeviceGammaRamp

GetDC.restype = HDC


class PHYSICAL_MONITOR(Structure):
    _fields_ = [('hPhysicalMonitor', HANDLE),
                ('szPhysicalMonitorDescription',
                 WCHAR * PHYSICAL_MONITOR_DESCRIPTION_SIZE)]


class MONITORINFO(Structure):
    _fields_ = [('cbSize', DWORD),
                ('rcMonitor', RECT),
                ('rcWork', RECT),
                ('dwFlags', DWORD)]


@contextmanager
def get_dc():
    hdc = HDC(GetDC(None))

    if not hdc:
        raise RuntimeError('Unable to open device context')

    try:
        queue = Queue()

        def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            hMonitor = HMONITOR(hMonitor)
            hdcMonitor = HDC(hdcMonitor)

            mi = MONITORINFO()
            mi.cbSize = sizeof(mi)

            if not GetMonitorInfo(hMonitor, byref(mi)):
                raise WinError()

            if mi.dwFlags & MONITORINFOF_PRIMARY and \
               GetDeviceCaps(hdcMonitor, COLORMGMTCAPS) & CM_GAMMA_RAMP:
                queue.put(hdcMonitor)
                queue.join()

            return True

        def worker():
            if not EnumDisplayMonitors(hdc, None, MONITORENUMPROC(callback),
                                       None):
                raise WinError()

            queue.put(None)

        thread = Thread(target=worker)
        thread.start()

        hdcMonitor = queue.get()

        try:
            if hdcMonitor is not None:
                yield hdcMonitor
        finally:
            queue.task_done()

            if hdcMonitor is not None:
                while queue.get() is not None:
                    queue.task_done()

                queue.task_done()

            thread.join()

        if hdcMonitor is None:
            yield hdc
    finally:
        if not ReleaseDC(None, hdc):
            raise RuntimeError('Unable to release device context')


class Context:
    def __init__(self):
        self._saved_ramp = (WORD * 256 * 3)()

        with get_dc() as hdc:
            cmcap = GetDeviceCaps(hdc, COLORMGMTCAPS)

            if not cmcap & CM_GAMMA_RAMP:
                raise RuntimeError('Display device does not support gamma '
                                   'ramps')

            if not GetDeviceGammaRamp(hdc, byref(self._saved_ramp)):
                raise RuntimeError('Unable to save current gamma '
                                   'ramp') from WinError()

    def set(self, func):
        ramp = (WORD * 256 * 3)()

        for i in range(256):
            ramp[0][i] = ramp[1][i] = ramp[2][i] = \
                int(WORD_MAX * func(i / 256))

        with get_dc() as hdc:
            if not SetDeviceGammaRamp(hdc, byref(ramp)):
                raise RuntimeError('Unable to set gamma ramp') from WinError()

    def set_default(self):
        ramp = (WORD * 256 * 3)()

        for i in range(256):
            ramp[0][i] = ramp[1][i] = ramp[2][i] = i << 8

        with get_dc() as hdc:
            if not SetDeviceGammaRamp(hdc, byref(ramp)):
                raise RuntimeError('Unable to set gamma ramp') from WinError()

    def close(self, restore=True):
        if restore:
            with get_dc() as hdc:
                if not SetDeviceGammaRamp(hdc, byref(self._saved_ramp)):
                    raise RuntimeError('Unable to restore gamma '
                                       'ramp') from WinError()
