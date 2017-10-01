import platform


__all__ = ['Context']

system = platform.system()

if system == 'Windows':
    from .context_wingdi import Context
elif system == 'Linux':
    from .context_vidmode import Context
elif system == 'Darwin':
    from .context_quartz import Context
else:
    raise NotImplementedError(system)
