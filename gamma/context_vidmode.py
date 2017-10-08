from ctypes import byref, sizeof, string_at, cdll, POINTER
from ctypes import c_ubyte, c_ushort, c_int, c_long, c_ulong, c_void_p
from ctypes.util import find_library
from .calibration import read_icc_ramp
from .context import Context, ContextError


__all__ = ['Context', 'ContextError']

c_uchar = c_ubyte
c_uchar_p = POINTER(c_uchar)

C_USHORT_SIZE = sizeof(c_ushort)
C_USHORT_MAX = c_ushort(~0).value

X11 = cdll.LoadLibrary(find_library('X11'))
Xxf86vm = cdll.LoadLibrary(find_library('Xxf86vm'))

XA_CARDINAL = 6

XNone = 0
XSuccess = 0

XWindow = c_ulong
XAtom = c_ulong

_XOpenDisplay = X11.XOpenDisplay
XCloseDisplay = X11.XCloseDisplay
XDefaultScreen = X11.XDefaultScreen
_XRootWindow = X11.XRootWindow
_XInternAtom = X11.XInternAtom
XGetWindowProperty = X11.XGetWindowProperty
XFree = X11.XFree
XF86VidModeGetGammaRampSize = Xxf86vm.XF86VidModeGetGammaRampSize
XF86VidModeGetGammaRamp = Xxf86vm.XF86VidModeGetGammaRamp
XF86VidModeSetGammaRamp = Xxf86vm.XF86VidModeSetGammaRamp

_XOpenDisplay.restype = c_void_p
_XInternAtom.restype = XAtom
_XRootWindow.restype = XWindow


def XOpenDisplay(display_name):
    return c_void_p(_XOpenDisplay(display_name))


def XRootWindow(display, screen_num):
    return XWindow(_XRootWindow(display, screen_num))


def XInternAtom(display, atom_name, only_if_exists):
    return XAtom(_XInternAtom(display, atom_name, only_if_exists))


class VidModeContext(Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        display = XOpenDisplay(None)

        if not display:
            raise ContextError('X request failed: XOpenDisplay')

        self._display = display

        screen_num = XDefaultScreen(display)
        self._screen_num = screen_num

        ramp_size = c_int()

        if not XF86VidModeGetGammaRampSize(display, screen_num,
                                           byref(ramp_size)):
            XCloseDisplay(display)
            raise ContextError('X request failed: XF86VidModeGetGammaRampSize')

        self.ramp_size = ramp_size.value

        if self.ramp_size <= 1:
            XCloseDisplay(display)
            raise ContextError('Gamma ramp size is too small')

    def get_ramp(self):
        display = self._display
        screen_num = self._screen_num

        ramp_size = self.ramp_size
        ramp = (c_ushort * ramp_size * 3)()

        gamma_r = byref(ramp, 0 * ramp_size * C_USHORT_SIZE)
        gamma_g = byref(ramp, 1 * ramp_size * C_USHORT_SIZE)
        gamma_b = byref(ramp, 2 * ramp_size * C_USHORT_SIZE)

        if not XF86VidModeGetGammaRamp(display, screen_num, ramp_size,
                                       gamma_r, gamma_g, gamma_b):
            raise ContextError('Unable to get gamma ramp')

        return [[ramp[i][j] / C_USHORT_MAX for j in range(ramp_size)]
                for i in range(3)]

    def set_ramp(self, ramp):
        display = self._display
        screen_num = self._screen_num

        ramp_size = self.ramp_size
        _ramp = (c_ushort * ramp_size * 3)()

        for i in range(3):
            for j in range(ramp_size):
                _ramp[i][j] = int(C_USHORT_MAX * ramp[i][j])

        gamma_r = byref(_ramp, 0 * ramp_size * C_USHORT_SIZE)
        gamma_g = byref(_ramp, 1 * ramp_size * C_USHORT_SIZE)
        gamma_b = byref(_ramp, 2 * ramp_size * C_USHORT_SIZE)

        if not XF86VidModeSetGammaRamp(display, screen_num, ramp_size,
                                       gamma_r, gamma_g, gamma_b):
            raise ContextError('Unable to set gamma ramp')

    def close(self):
        try:
            display = self._display
            screen_num = self._screen_num

            ramp_size = self.ramp_size
            ramp = (c_ushort * ramp_size * 3)()

            prop = XInternAtom(display, b'_ICC_PROFILE', True)

            if prop.value != XNone:
                window = XRootWindow(display, screen_num)

                actual_type = XAtom()
                actual_format = c_int()
                nitems = c_ulong()
                bytes_after = c_ulong()
                data = c_uchar_p()

                if XGetWindowProperty(display, window, prop, c_long(0),
                                      c_long(0), False, XAtom(XA_CARDINAL),
                                      byref(actual_type), byref(actual_format),
                                      byref(nitems), byref(bytes_after),
                                      byref(data)) != XSuccess:
                    raise ContextError('X request failed: XGetWindowProperty')

                if data:
                    XFree(data)

                if XGetWindowProperty(display, window, prop, c_long(0),
                                      c_long(bytes_after.value // 4), False,
                                      XAtom(XA_CARDINAL), byref(actual_type),
                                      byref(actual_format), byref(nitems),
                                      byref(bytes_after),
                                      byref(data)) != XSuccess:
                    raise ContextError('X request failed: XGetWindowProperty')

                assert bytes_after.value == 0

                profile = string_at(data, nitems.value)

                XFree(data)

                try:
                    icc_ramp = read_icc_ramp(profile, size=ramp_size)

                    for i in range(3):
                        for j in range(ramp_size):
                            ramp[i][j] = int(C_USHORT_MAX * icc_ramp[i][j])
                except:
                    for i in range(3):
                        for j in range(ramp_size):
                            ramp[i][j] = C_USHORT_MAX * j // 255
            else:
                for i in range(3):
                    for j in range(ramp_size):
                        ramp[i][j] = C_USHORT_MAX * j // 255

            gamma_r = byref(ramp, 0 * ramp_size * C_USHORT_SIZE)
            gamma_g = byref(ramp, 1 * ramp_size * C_USHORT_SIZE)
            gamma_b = byref(ramp, 2 * ramp_size * C_USHORT_SIZE)

            if not XF86VidModeSetGammaRamp(display, screen_num, ramp_size,
                                           gamma_r, gamma_g, gamma_b):
                raise ContextError('Unable to restore gamma ramp')
        finally:
            XCloseDisplay(display)
