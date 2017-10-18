import os
import struct
import subprocess
import sys
from ctypes import byref, sizeof, Structure
from argparse import ArgumentParser, ArgumentTypeError
from ctypes.wintypes import WCHAR, WORD
from inject import Process


FIND_PROCESS = '''& {
Param([string]$name, [string]$path, [string]$thumbprint);

if ($path) {
    if (-Not [System.IO.Path]::IsPathRooted($path)) {
        $path = Join-Path (pwd) $path;
    }
    $path = [System.IO.Path]::GetFullPath($path);
}

Foreach ($process in Get-Process) {
    If (-Not $name -Or $process.Name -Eq $name) {
        If (-Not $path -Or $process.Path -Eq $path) {
            If (-Not $thumbprint) {
                Exit $process.Id;
            }

            $signature = Get-AuthenticodeSignature -File $process.Path;

            If ($signature.Status -Eq 'Valid' -And
                $signature.SignerCertificate.Thumbprint -Eq $thumbprint) {
                Exit $process.Id;
            }
        }
    }
}
Exit 0;
}'''


def process_type(s):
    s = s.strip()

    try:
        pid = int(s)
    except:
        try:
            name, path, thumbprint = s.split(':')
        except:
            raise ArgumentTypeError('invalid process descriptor: '
                                    'expected name:path:thumbprint')

        cmd = ['PowerShell', '-Command', FIND_PROCESS]

        if name:
            cmd += ['-Name', name]

        if path:
            cmd += ['-Path', path]

        if thumbprint:
            cmd += ['-Thumbprint', thumbprint]

        pid = subprocess.call(cmd)

        if pid == 0:
            raise ArgumentTypeError('process not found')

    if not (pid > 0 and pid <= 2**32-1):
        raise ArgumentTypeError('invalid process ID')

    try:
        process = Process(pid)
    except:
        raise ArgumentTypeError('unable to open process')

    return process


def ip_address_type(s):
    ip_address = s.strip()
    digits = ip_address.split('.')

    if not (len(digits) == 4 and all(x.isdigit() and int(x) >= 0 and
            int(x) <= 255 for x in digits)):
        raise ArgumentTypeError('malformed IP address')

    return ip_address


def port_type(s):
    try:
        port = int(s)
    except:
        raise ArgumentTypeError('malformed port')

    if not (port >= 0 and port <= 65535):
        raise ArgumentTypeError('invalid port')

    return port


if __name__ == '__main__':
    if getattr(sys, 'frozen', False):
        path = os.path.dirname(sys.executable)
    elif __file__:
        path = os.path.dirname(__file__)

    parser = ArgumentParser(prog='hook')
    parser.add_argument('command', choices=('start', 'stop'))

    args = parser.parse_args(sys.argv[1:2])

    if args.command == 'start':
        parser = ArgumentParser(prog='hook start')
        parser.add_argument('process', type=process_type)
        parser.add_argument('--host', type=ip_address_type, required=True)
        parser.add_argument('--port', type=port_type, required=True)

        args = parser.parse_args(sys.argv[2:])

        process = args.process
        host = args.host
        port = args.port

        try:
            hook_path = os.path.join(path, 'hook{}.dll'.format(process.bits))

            hook = process.get_module(hook_path)

            if hook is None:
                hook = process.inject_module(hook_path, auto_eject=False)

            hook_addr = hook.get_proc_address('Hook')

            if process.bits == 64:
                patch = b'\x48\xB8' + struct.pack('<Q', hook_addr.value)
            else:
                patch = b'\xB8' + struct.pack('<L', hook_addr.value)

            patch += b'\xFF\xE0'

            process.write_memory(
                    process.get_module(name='gdi32').
                    get_proc_address('SetDeviceGammaRamp'), patch, len(patch))

            class HookParam(Structure):
                _fields_ = [('serverName', WCHAR * 16),
                            ('serverPort', WORD)]

            hook_param = HookParam()
            hook_param.serverName = host
            hook_param.serverPort = port

            with process.alloc_memory(sizeof(hook_param)) as param:
                param.write(byref(hook_param), sizeof(hook_param))

                if not hook.call_proc('HookStart', param.address):
                    raise RuntimeError('Failed to start hook')
        finally:
            process.close()
    elif args.command == 'stop':
        parser = ArgumentParser(prog='hook stop')
        parser.add_argument('process', type=process_type)

        args = parser.parse_args(sys.argv[2:])

        process = args.process

        try:
            hook_path = os.path.join(path, 'hook{}.dll'.format(process.bits))

            hook = process.get_module(hook_path)

            if hook is not None:
                if not hook.call_proc('HookStop'):
                    raise RuntimeError('Failed to stop hook')
        finally:
            process.close()
    else:
        assert False
