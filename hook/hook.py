import os
import platform
import struct
import subprocess
from ctypes import create_string_buffer, byref, sizeof, Structure
from ctypes.wintypes import WCHAR, WORD

if platform.system() == 'Windows':
    from .inject import Process

__all__ = ['Hook']


class Hook:
    def __init__(self, app, enable=True):
        self.enable = enable

        if enable and platform.system() == 'Windows':
            flux = subprocess.call(['PowerShell', '-Command', '''& {
                Foreach ($p in Get-Process) {
                    if ($p.Name -Eq "flux") {
                        $s = Get-AuthenticodeSignature -File $p.Path;
                        If ($s.Status -Eq "Valid" -And
                            $s.SignerCertificate.Thumbprint -Eq
                            "36E504701938FEA480DB816490D6EAE042EB7907") {
                            Exit $p.Id; } } } Exit 0; }'''])

            if not flux:
                flux = None
            else:
                flux = Process(flux)

                try:
                    hook_path = os.path.join(
                            app.path, 'hook/hook{}.dll'.format(flux.bits))

                    flux_hook = flux.get_module(hook_path)

                    if flux_hook is None:
                        flux_hook = flux.inject_module(hook_path,
                                                       auto_eject=False)

                    class HookParam(Structure):
                        _fields_ = [('serverName', WCHAR * 16),
                                    ('serverPort', WORD)]

                    hook_param = HookParam()
                    hook_param.serverName = app.host[:15]
                    hook_param.serverPort = app.port

                    with flux.alloc_memory(sizeof(hook_param)) as param:
                        param.write(byref(hook_param), sizeof(hook_param))

                        if not flux_hook.call_proc('HookStart', param.address):
                            raise RuntimeError('Failed to start hook')

                    hook_addr = flux_hook.get_proc_address('Hook')
                    flux_addr = flux.get_module(name='gdi32'). \
                        get_proc_address('SetDeviceGammaRamp')

                    if flux.bits == 64:
                        patched = b'\x48\xB8' + struct.pack('<Q',
                                                            hook_addr.value)
                    else:
                        patched = b'\xB8' + struct.pack('<L', hook_addr.value)

                    patched += b'\xFF\xE0'
                    unpatched = create_string_buffer(len(patched))

                    flux.read_memory(flux_addr, unpatched, len(unpatched))
                    flux.write_memory(flux_addr, patched, len(patched))

                    self.flux_hook = flux_hook
                    self.flux_addr = flux_addr
                    self.flux_unpatched = unpatched.raw
                except:
                    flux.close()
                    raise

            self.flux = flux

    def unhook(self):
        if self.enable and platform.system() == 'Windows' and self.flux:

            try:
                if self.flux.is_still_alive():
                    if self.flux_hook:
                        try:
                            self.flux.write_memory(self.flux_addr,
                                                   self.flux_unpatched,
                                                   len(self.flux_unpatched))
                        finally:
                            if not self.flux_hook.call_proc('HookStop'):
                                raise RuntimeError('Failed to stop hook')
            finally:
                self.flux.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.unhook()
