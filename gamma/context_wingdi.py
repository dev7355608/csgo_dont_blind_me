from contextlib import contextmanager
from ctypes import byref, sizeof, Structure, windll, WinError
from ctypes import create_unicode_buffer, POINTER
from ctypes.wintypes import DWORD, HDC, WCHAR, WORD
from winreg import HKEY_LOCAL_MACHINE, OpenKey, CloseKey, QueryValueEx
from .calibration import read_icc_ramp
from .context import Context, ContextError


__all__ = ['Context']

ICM_KEY = 'SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM'

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
_CreateIC = windll.gdi32.CreateICW
DeleteDC = windll.gdi32.DeleteDC
_GetDC = windll.user32.GetDC
ReleaseDC = windll.user32.ReleaseDC
GetICMProfile = windll.gdi32.GetICMProfileW
GetDeviceCaps = windll.gdi32.GetDeviceCaps
GetDeviceGammaRamp = windll.gdi32.GetDeviceGammaRamp
_SetDeviceGammaRamp = windll.gdi32.SetDeviceGammaRamp

EnumDisplayDevices.argtypes = [POINTER(WCHAR), DWORD, POINTER(DISPLAY_DEVICE),
                               DWORD]
_CreateIC.restype = HDC
_GetDC.restype = HDC


def CreateDC(driver, device, output, initData):
    return HDC(_CreateIC(driver, device, output, initData))


def GetDC(hWnd):
    return HDC(_GetDC(hWnd))


def SetDeviceGammaRamp(hDC, lpRamp):
    for _ in range(10):
        if _SetDeviceGammaRamp(hDC, lpRamp):
            return 1

    return 0


class WinGdiContext(Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
            raise ContextError('No primary display device exists')

        hdc = CreateDC(None, device_name, None, None)
        self._hdc = hdc

        if not hdc:
            raise ContextError('Unable to create device context') \
                  from WinError()

        cmcap = GetDeviceCaps(hdc, COLORMGMTCAPS)

        if not cmcap & CM_GAMMA_RAMP:
            if not DeleteDC(hdc):
                raise ContextError('Unable to delete device context') \
                      from WinError()

            del hdc
            self._hdc = None

        try:
            with self._get_dc() as hdc:
                cmcap = GetDeviceCaps(hdc, COLORMGMTCAPS)

                if not cmcap & CM_GAMMA_RAMP:
                    raise ContextError('Display device does not support gamma '
                                       'ramps') from WinError()

            try:
                key = None
                key = OpenKey(HKEY_LOCAL_MACHINE, ICM_KEY)
                gamma_range = QueryValueEx(key, 'GdiIcmGammaRange')[0]
            except FileNotFoundError:
                gamma_range = None
            finally:
                if key is not None:
                    CloseKey(key)

            if gamma_range != 256:
                raise ContextError('Gamma range is currently limited; please '
                                   'unlock it!')
        except:
            if self._hdc is not None:
                DeleteDC(self._hdc)
            raise

        self.ramp_size = 256

    @contextmanager
    def _get_dc(self):
        hdc = self._hdc

        if hdc is None:
            hdc = GetDC(None)

            if not hdc:
                raise ContextError('Unable to open device context')

            try:
                yield hdc
            finally:
                if not ReleaseDC(None, hdc):
                    raise ContextError('Unable to release device context')
        else:
            yield hdc

    def get_ramp(self):
        with self._get_dc() as hdc:
            ramp = (WORD * 256 * 3)()

            if not GetDeviceGammaRamp(hdc, byref(ramp)):
                raise ContextError('Unable to get gamma ramp') \
                      from WinError()

            return [[ramp[i][j] / 65535 for j in range(256)] for i in range(3)]

    def set_ramp(self, ramp):
        _ramp = (WORD * 256 * 3)()

        for i in range(3):
            for j in range(256):
                _ramp[i][j] = int(65535 * ramp[i][j])

        with self._get_dc() as hdc:
            if not SetDeviceGammaRamp(hdc, byref(_ramp)):
                raise ContextError('Unable to set gamma ramp; has the gamma '
                                   'range been unlocked yet?') from WinError()

    def close(self):
        try:
            with self._get_dc() as hdc:
                cbName = DWORD(0)

                GetICMProfile(hdc, byref(cbName), None)

                filename = create_unicode_buffer(cbName.value)

                GetICMProfile(hdc, byref(cbName), filename)

                with open(filename.value, mode='rb') as f:
                    icc_ramp = read_icc_ramp(f, size=256)

                ramp = (WORD * 256 * 3)()

                for i in range(3):
                    for j in range(256):
                        ramp[i][j] = int(255 * icc_ramp[i][j] + 0.5) << 8

                if not SetDeviceGammaRamp(hdc, byref(ramp)):
                    raise ContextError('Unable to restore gamma ramp') \
                          from WinError()
        finally:
            if self._hdc is not None:
                if not DeleteDC(self._hdc):
                    raise ContextError('Unable to delete device context') \
                          from WinError()
