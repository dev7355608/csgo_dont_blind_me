from ctypes import byref, sizeof, Structure, windll, WinError
from ctypes import POINTER
from ctypes.wintypes import DWORD, HDC, WCHAR, WORD


__all__ = ['Context']

WORD_MAX = pow(2, sizeof(WORD) * 8) - 1

DISPLAY_DEVICE_PRIMARY_DEVICE = 4

COLORMGMTCAPS = 121
CM_GAMMA_RAMP = 2


class DISPLAY_DEVICE(Structure):
    _fields_ = [('cb', DWORD),
                ('DeviceName', WCHAR * 32),
                ('DeviceString', WCHAR * 128),
                ('StateFlags', DWORD),
                ('DeviceID', WCHAR * 128),
                ('DeviceKey', WCHAR * 128)]


EnumDisplayDevices = windll.user32.EnumDisplayDevicesW
CreateIC = windll.gdi32.CreateICW
DeleteDC = windll.gdi32.DeleteDC
GetDeviceCaps = windll.gdi32.GetDeviceCaps
GetDeviceGammaRamp = windll.gdi32.GetDeviceGammaRamp
SetDeviceGammaRamp = windll.gdi32.SetDeviceGammaRamp

EnumDisplayDevices.argtypes = [POINTER(WCHAR), DWORD, POINTER(DISPLAY_DEVICE),
                               DWORD]
CreateIC.restype = HDC


class Context:
    def __init__(self):
        device = DISPLAY_DEVICE()
        device.cb = sizeof(device)
        device_num = 0
        device_name = None

        while EnumDisplayDevices(None, device_num, byref(device), 0):
            if device.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE:
                device_name = device.DeviceName
                break

            device_num += 1

        if device_name is None:
            raise RuntimeError('No primary display device exists')

        hdc = HDC(CreateIC(None, device_name, None, None))
        self._hdc = hdc

        if not hdc:
            raise RuntimeError('Unable to create device context') \
                  from WinError()

        try:
            cmcap = GetDeviceCaps(hdc, COLORMGMTCAPS)

            if not cmcap & CM_GAMMA_RAMP:
                raise RuntimeError('Display device does not support gamma '
                                   'ramps')

            self._saved_ramp = (WORD * 256 * 3)()

            if not GetDeviceGammaRamp(hdc, byref(self._saved_ramp)):
                raise RuntimeError('Unable to save current gamma ramp') \
                      from WinError()
        except:
            DeleteDC(hdc)
            raise

    def set(self, func):
        ramp = (WORD * 256 * 3)()

        for i in range(256):
            ramp[0][i] = ramp[1][i] = ramp[2][i] = \
                int(WORD_MAX * func(i / 256))

        if not SetDeviceGammaRamp(self._hdc, byref(ramp)):
            raise RuntimeError('Unable to set gamma ramp') from WinError()

    def set_default(self):
        ramp = (WORD * 256 * 3)()

        for i in range(256):
            ramp[0][i] = ramp[1][i] = ramp[2][i] = i << 8

        if not SetDeviceGammaRamp(self._hdc, byref(ramp)):
            raise RuntimeError('Unable to set gamma ramp') from WinError()

    def close(self, restore=True):
        try:
            if restore:
                if not SetDeviceGammaRamp(self._hdc, byref(self._saved_ramp)):
                    raise RuntimeError('Unable to restore gamma ramp') \
                          from WinError()
        finally:
            if not DeleteDC(self._hdc):
                raise RuntimeError('Unable to delete device context') \
                      from WinError()
