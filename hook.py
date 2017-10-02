import atexit
import sys
from time import sleep


class Exit:
    def __init__(self, exit, exithook):
        self.exit = exit
        self.exithook = exithook

    def __call__(self, code=0):
        self.exithook.exit_code = code
        self.exit(code)


class ExceptHook:
    def __init__(self, excepthook, exithook):
        self.excepthook = excepthook
        self.exithook = exithook

    def __call__(self, type, value, traceback):
        self.exithook.exception = (type, value, traceback)
        self.excepthook(type, value, traceback)


class ExitHook:
    def __init__(self):
        self.exception = None
        self.exit_code = None

    def __call__(self):
        if self.exit_code not in (None, 0) or self.exception is not None:
            print('\n\nPress CTRL+C to exit...')

            try:
                while True:
                    sleep(1)
            except KeyboardInterrupt:
                pass


exithook = ExitHook()
atexit.register(exithook)
sys.exit = Exit(sys.exit, exithook)
sys.excepthook = ExceptHook(sys.excepthook, exithook)
