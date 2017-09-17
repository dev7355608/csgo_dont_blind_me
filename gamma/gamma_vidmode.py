from ctypes import byref, c_int, c_uint16, cdll
from ctypes.util import find_library


__all__ = ['Context']

X11 = cdll.LoadLibrary(find_library('X11'))
Xxf86vm = cdll.LoadLibrary(find_library('Xxf86vm'))

XOpenDisplay = X11.XOpenDisplay
XCloseDisplay = X11.XCloseDisplay
XDefaultScreen = X11.XDefaultScreen
XF86VidModeQueryVersion = Xxf86vm.XF86VidModeQueryVersion
XF86VidModeGetGammaRampSize = Xxf86vm.XF86VidModeGetGammaRampSize
XF86VidModeGetGammaRamp = Xxf86vm.XF86VidModeGetGammaRamp
XF86VidModeSetGammaRamp = Xxf86vm.XF86VidModeSetGammaRamp


class Context:
    def __init__(self):
        display = XOpenDisplay(None)

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

        if ramp_size == 0:
            XCloseDisplay(display)
            raise RuntimeError('Gamma ramp size is zero')

        ramp = (c_uint16 * ramp_size * 3)()

        gamma_r = byref(ramp, 0 * ramp_size)
        gamma_g = byref(ramp, 1 * ramp_size)
        gamma_b = byref(ramp, 2 * ramp_size)

        if not XF86VidModeGetGammaRamp(display, screen_num, ramp_size,
                                       gamma_r, gamma_g, gamma_b):
            XCloseDisplay(display)
            raise RuntimeError('X request failed: XF86VidModeGetGammaRamp')

        self._saved_ramp = ramp

    def set(self, func):
        display = self._display
        screen_num = self._screen_num

        ramp_size = self._ramp_size
        ramp = (c_uint16 * ramp_size * 3)()

        for i in range(ramp_size):
            ramp[0][i] = ramp[1][i] = ramp[2][i] = func(i / ramp_size)

        gamma_r = byref(ramp, 0 * ramp_size)
        gamma_g = byref(ramp, 1 * ramp_size)
        gamma_b = byref(ramp, 2 * ramp_size)

        if not XF86VidModeSetGammaRamp(display, screen_num, ramp_size,
                                       gamma_r, gamma_g, gamma_b):
            raise RuntimeError('X request failed: XF86VidModeSetGammaRamp')

    def close(self):
        try:
            display = self._display
            screen_num = self._screen_num

            ramp_size = self._ramp_size
            ramp = self._saved_ramp

            gamma_r = byref(ramp, 0 * ramp_size)
            gamma_g = byref(ramp, 1 * ramp_size)
            gamma_b = byref(ramp, 2 * ramp_size)

            if not XF86VidModeSetGammaRamp(display, screen_num, ramp_size,
                                           gamma_r, gamma_g, gamma_b):
                raise RuntimeError('X request failed: XF86VidModeSetGammaRamp')
        finally:
            XCloseDisplay(display)
