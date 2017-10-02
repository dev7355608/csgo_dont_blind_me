import platform


__all__ = ['Context', 'ContextError']


class ContextError(Exception):
    pass


class Context:

    def open(*args, **kwargs):
        return _Context(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()


system = platform.system()

if system == 'Windows':
    from .context_wingdi import WinGdiContext as _Context
elif system == 'Linux':
    from .context_vidmode import VidModeContext as _Context
elif system == 'Darwin':
    from .context_quartz import QuartzContext as _Context
else:
    raise NotImplementedError(system)
