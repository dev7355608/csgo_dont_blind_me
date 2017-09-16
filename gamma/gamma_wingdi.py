from contextlib import contextmanager
from ctypes import byref, windll, WinError
from ctypes.wintypes import WORD


__all__ = ['Context']

GAMMA_RAMP_SIZE = 256
COLORMGMTCAPS = 121
CM_GAMMA_RAMP = 2

GetDC = windll.user32.GetDC
ReleaseDC = windll.user32.ReleaseDC
GetDeviceCaps = windll.gdi32.GetDeviceCaps
GetDeviceGammaRamp = windll.gdi32.GetDeviceGammaRamp
SetDeviceGammaRamp = windll.gdi32.SetDeviceGammaRamp


@contextmanager
def get_dc():
    hdc = GetDC(None)

    if not hdc:
        raise RuntimeError('Unable to open get_dc context')

    try:
        yield hdc
    finally:
        if not ReleaseDC(None, hdc):
            raise RuntimeError('Unable to release get_dc context')


class Context:
    def __init__(self):
        self._saved_ramps = []

        with get_dc() as hdc:
            cmcap = GetDeviceCaps(hdc, COLORMGMTCAPS)

            if not cmcap & CM_GAMMA_RAMP:
                raise RuntimeError('Display get_dc does not support gamma '
                                   'ramps') from WinError()

    def save(self):
        with get_dc() as hdc:
            ramp = (WORD * GAMMA_RAMP_SIZE * 3)()

            if not GetDeviceGammaRamp(hdc, byref(ramp)):
                raise RuntimeError('Unable to save current gamma '
                                   'ramp') from WinError()

            self._saved_ramps.append(ramp)

    def restore(self):
        with get_dc() as hdc:
            ramp = self._saved_ramps.pop()

            if not SetDeviceGammaRamp(hdc, byref(ramp)):
                raise RuntimeError('Unable to restore gamma '
                                   'ramp') from WinError()

    def set(self, func):
        ramp = (WORD * GAMMA_RAMP_SIZE * 3)()

        for j in range(GAMMA_RAMP_SIZE):
            ramp[0][j] = ramp[1][j] = ramp[2][j] = \
                int(65535 * func(j / GAMMA_RAMP_SIZE))

        with get_dc() as hdc:
            if not SetDeviceGammaRamp(hdc, byref(ramp)):
                raise RuntimeError('Unable to set gamma ramp') from WinError()

    def destroy(self):
        pass
