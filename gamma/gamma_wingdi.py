from contextlib import contextmanager
from ctypes import byref, sizeof, windll, WinError
from ctypes.wintypes import WORD, HDC


__all__ = ['Context']

WORD_MAX = pow(2, sizeof(WORD) * 8) - 1

COLORMGMTCAPS = 121
CM_GAMMA_RAMP = 2

GetDC = windll.user32.GetDC
ReleaseDC = windll.user32.ReleaseDC
GetDeviceCaps = windll.gdi32.GetDeviceCaps
GetDeviceGammaRamp = windll.gdi32.GetDeviceGammaRamp
SetDeviceGammaRamp = windll.gdi32.SetDeviceGammaRamp

GetDC.restype = HDC


@contextmanager
def get_dc():
    hdc = HDC(GetDC(None))

    if not hdc:
        raise RuntimeError('Unable to open device context')

    try:
        yield hdc
    finally:
        if not ReleaseDC(None, hdc):
            raise RuntimeError('Unable to release device context')


class Context:
    def __init__(self):
        with get_dc() as hdc:
            cmcap = GetDeviceCaps(hdc, COLORMGMTCAPS)

            if not cmcap & CM_GAMMA_RAMP:
                raise RuntimeError('Display device does not support gamma '
                                   'ramps') from WinError()

            self._saved_ramp = (WORD * 256 * 3)()

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

    def close(self):
        with get_dc() as hdc:
            if not SetDeviceGammaRamp(hdc, byref(self._saved_ramp)):
                raise RuntimeError('Unable to restore gamma '
                                   'ramp') from WinError()
