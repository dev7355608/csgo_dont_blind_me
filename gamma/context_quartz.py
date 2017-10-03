from ctypes import byref, sizeof, c_float, c_uint32, cdll
from ctypes.util import find_library
from .context import Context, ContextError


__all__ = ['Context', 'ContextError']

C_FLOAT_SIZE = sizeof(c_float)

lib = cdll.LoadLibrary(find_library('ApplicationServices'))

kCGErrorSuccess = 0

CGDirectDisplayID = c_uint32

_CGMainDisplayID = lib.CGMainDisplayID
_CGDisplayGammaTableCapacity = lib.CGDisplayGammaTableCapacity
CGGetDisplayTransferByTable = lib.CGGetDisplayTransferByTable
CGSetDisplayTransferByTable = lib.CGSetDisplayTransferByTable
CGDisplayRestoreColorSyncSettings = lib.CGDisplayRestoreColorSyncSettings

_CGMainDisplayID.restype = CGDirectDisplayID
_CGDisplayGammaTableCapacity.restype = c_uint32


def CGMainDisplayID():
    return CGDirectDisplayID(_CGMainDisplayID())


def CGDisplayGammaTableCapacity(display):
    return c_uint32(_CGDisplayGammaTableCapacity(display)).value


class QuartzContext(Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._display = CGMainDisplayID()
        self.ramp_size = CGDisplayGammaTableCapacity(self._display)

        if self.ramp_size <= 1:
            raise ContextError('Gamma ramp size is too small')

    def get_ramp(self):
        ramp_size = self.ramp_size
        ramp = (c_float * ramp_size * 3)()

        gamma_r = byref(ramp, 0 * ramp_size * C_FLOAT_SIZE)
        gamma_g = byref(ramp, 1 * ramp_size * C_FLOAT_SIZE)
        gamma_b = byref(ramp, 2 * ramp_size * C_FLOAT_SIZE)

        sample_count = c_uint32()

        error = CGGetDisplayTransferByTable(self._display, c_uint32(ramp_size),
                                            gamma_r, gamma_g, gamma_b,
                                            byref(sample_count))

        if error != kCGErrorSuccess:
            raise ContextError('Unable to get gamma ramp')

        assert sample_count.value == ramp_size

        return [[ramp[i][j] for j in range(ramp_size)] for i in range(3)]

    def set_ramp(self, ramp):
        ramp_size = self.ramp_size
        _ramp = (c_float * ramp_size * 3)()

        for i in range(3):
            for j in range(ramp_size):
                _ramp[i][j] = ramp[i][j]

        gamma_r = byref(_ramp, 0 * ramp_size * C_FLOAT_SIZE)
        gamma_g = byref(_ramp, 1 * ramp_size * C_FLOAT_SIZE)
        gamma_b = byref(_ramp, 2 * ramp_size * C_FLOAT_SIZE)

        error = CGSetDisplayTransferByTable(self._display, c_uint32(ramp_size),
                                            gamma_r, gamma_g, gamma_b)

        if error != kCGErrorSuccess:
            raise ContextError('Unable to set gamma ramp')

    def close(self):
        CGDisplayRestoreColorSyncSettings()
