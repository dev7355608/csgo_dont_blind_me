from ctypes import byref, c_int, c_ushort, c_void_p, sizeof, cdll
from ctypes.util import find_library


__all__ = ['Context']

C_USHORT_MAX = pow(2, sizeof(c_ushort) * 8) - 1

X11 = cdll.LoadLibrary(find_library('X11'))
Xxf86vm = cdll.LoadLibrary(find_library('Xxf86vm'))

XOpenDisplay = X11.XOpenDisplay
XCloseDisplay = X11.XCloseDisplay
XDefaultScreen = X11.XDefaultScreen
XF86VidModeQueryVersion = Xxf86vm.XF86VidModeQueryVersion
XF86VidModeGetGammaRampSize = Xxf86vm.XF86VidModeGetGammaRampSize
XF86VidModeGetGammaRamp = Xxf86vm.XF86VidModeGetGammaRamp
XF86VidModeSetGammaRamp = Xxf86vm.XF86VidModeSetGammaRamp

XOpenDisplay.restype = c_void_p


class Context:
    def __init__(self):
        display = c_void_p(XOpenDisplay(None))

        if not display:
            raise RuntimeError('X request failed: XOpenDisplay')

        self._display = display

        screen_num = XDefaultScreen(display)
        self._screen_num = screen_num

        major = c_int()
        minor = c_int()

        if not XF86VidModeQueryVersion(display, byref(major), byref(minor)):
            XCloseDisplay(display)
            raise RuntimeError('X request failed: XF86VidModeQueryVersion')

        ramp_size = c_int()

        if not XF86VidModeGetGammaRampSize(display, screen_num,
                                           byref(ramp_size)):
            XCloseDisplay(display)
            raise RuntimeError('X request failed: XF86VidModeGetGammaRampSize')

        ramp_size = ramp_size.value
        self._ramp_size = ramp_size

        if ramp_size == 0:
            XCloseDisplay(display)
            raise RuntimeError('Gamma ramp size is zero')

        ramp = (c_ushort * ramp_size * 3)()

        gamma_r = byref(ramp, 0 * ramp_size * sizeof(c_ushort))
        gamma_g = byref(ramp, 1 * ramp_size * sizeof(c_ushort))
        gamma_b = byref(ramp, 2 * ramp_size * sizeof(c_ushort))

        if not XF86VidModeGetGammaRamp(display, screen_num, ramp_size,
                                       gamma_r, gamma_g, gamma_b):
            XCloseDisplay(display)
            raise RuntimeError('X request failed: XF86VidModeGetGammaRamp')

        self._saved_ramp = ramp

    def set(self, func):
        display = self._display
        screen_num = self._screen_num

        ramp_size = self._ramp_size
        ramp = (c_ushort * ramp_size * 3)()

        for i in range(ramp_size):
            ramp[0][i] = ramp[1][i] = ramp[2][i] = \
                int(C_USHORT_MAX * func(i / ramp_size))

        gamma_r = byref(ramp, 0 * ramp_size * sizeof(c_ushort))
        gamma_g = byref(ramp, 1 * ramp_size * sizeof(c_ushort))
        gamma_b = byref(ramp, 2 * ramp_size * sizeof(c_ushort))

        if not XF86VidModeSetGammaRamp(display, screen_num, ramp_size,
                                       gamma_r, gamma_g, gamma_b):
            raise RuntimeError('X request failed: XF86VidModeSetGammaRamp')

    def close(self):
        try:
            display = self._display
            screen_num = self._screen_num

            ramp_size = self._ramp_size
            ramp = self._saved_ramp

            gamma_r = byref(ramp, 0 * ramp_size * sizeof(c_ushort))
            gamma_g = byref(ramp, 1 * ramp_size * sizeof(c_ushort))
            gamma_b = byref(ramp, 2 * ramp_size * sizeof(c_ushort))

            if not XF86VidModeSetGammaRamp(display, screen_num, ramp_size,
                                           gamma_r, gamma_g, gamma_b):
                raise RuntimeError('X request failed: XF86VidModeSetGammaRamp')
        finally:
            XCloseDisplay(display)
