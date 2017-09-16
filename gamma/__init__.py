import platform as _platform


_system = _platform.system()

if _system == 'Windows':
    from .gamma_wingdi import Context
elif _system == 'Linux':
    raise NotImplementedError(_system)
elif _system == 'Darwin':
    raise NotImplementedError(_system)
else:
    raise NotImplementedError(_system)
