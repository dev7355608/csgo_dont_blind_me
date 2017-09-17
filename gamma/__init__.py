import platform as _platform


_system = _platform.system()

if _system == 'Windows':
    from .gamma_wingdi import Context
elif _system == 'Linux':
    from .gamma_vidmode import Context
elif _system == 'Darwin':
    from .gamma_quartz import Context
else:
    raise NotImplementedError(_system)
