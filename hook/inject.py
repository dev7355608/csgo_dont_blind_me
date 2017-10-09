import os
import pathlib
import subprocess
import sys
import tempfile
import zlib
from base64 import b64decode
from ctypes import (byref, c_uint, c_uint32, c_uint64, cast, sizeof, Structure,
                    windll, WinError, create_unicode_buffer)
from ctypes import POINTER, WINFUNCTYPE
from ctypes.wintypes import (BOOL, BYTE, CHAR, DWORD, HANDLE, HMODULE, LPCSTR,
                             LPCVOID, LPCWSTR, LPDWORD, LPVOID, WCHAR, WPARAM)

__all__ = ['Process']

SIZE_T = WPARAM

kernel32 = windll.kernel32

PROCESS_ALL_ACCESS = 0x00F0000 | 0x00100000 | 0xFFF
PROCESS_CREATE_THREAD = 0x0002
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
SYNCHRONIZE = 0x00100000

_OpenProcess = kernel32.OpenProcess
_OpenProcess.argtypes = [DWORD, BOOL, DWORD]
_OpenProcess.restype = HANDLE


def OpenProcess(dwDesiredAccess, bInheritHandle, dwProcessId):
    return HANDLE(_OpenProcess(dwDesiredAccess, bInheritHandle, dwProcessId))


MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
PAGE_EXECUTE = 0x10
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40

_VirtualAllocEx = kernel32.VirtualAllocEx
_VirtualAllocEx.argtypes = [HANDLE, LPVOID, SIZE_T, DWORD, DWORD]
_VirtualAllocEx.restype = LPVOID


def VirtualAllocEx(hProcess, lpAddress, dwSize, flAllocationType, flProtect):
    return LPVOID(_VirtualAllocEx(hProcess, lpAddress, SIZE_T(dwSize),
                                  flAllocationType, flProtect))


VirtualProtectEx = kernel32.VirtualProtectEx
VirtualProtectEx.argtypes = [HANDLE, LPVOID, SIZE_T, DWORD, POINTER(DWORD)]
VirtualProtectEx.restype = BOOL

WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.argtypes = [HANDLE, LPVOID, LPCVOID, SIZE_T,
                               POINTER(SIZE_T)]
WriteProcessMemory.restype = BOOL

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [HANDLE, LPCVOID, LPVOID, SIZE_T,
                              POINTER(SIZE_T)]
ReadProcessMemory.restype = BOOL

_GetModuleHandleW = kernel32.GetModuleHandleW
_GetModuleHandleW.argtypes = [LPCWSTR]
_GetModuleHandleW.restype = HMODULE


def GetModuleHandleW(lpModuleName):
    return HMODULE(_GetModuleHandleW(lpModuleName))


_GetProcAddress = kernel32.GetProcAddress
_GetProcAddress.argtypes = [HMODULE, LPCSTR]
_GetProcAddress.restype = LPVOID


def GetProcAddress(hModule, lpProcName):
    return LPVOID(_GetProcAddress(hModule, lpProcName))


class SECURITY_ATTRIBUTES(Structure):
    _fields_ = [('nLength', DWORD),
                ('lpSecurityDescriptor', LPVOID),
                ('bInheritHandle', BOOL)]


LPSECURITY_ATTRIBUTES = POINTER(SECURITY_ATTRIBUTES)
LPTHREAD_START_ROUTINE = WINFUNCTYPE(DWORD, LPVOID)

_CreateRemoteThread = kernel32.CreateRemoteThread
_CreateRemoteThread.argtypes = [HANDLE, LPSECURITY_ATTRIBUTES, SIZE_T,
                                LPTHREAD_START_ROUTINE, LPVOID, DWORD, LPDWORD]
_CreateRemoteThread.restype = HANDLE


def CreateRemoteThread(hProcess, lpThreadAttributes, dwStackSize,
                       lpStartAddress, lpParameter, dwCreationFlags,
                       lpThreadId):
    return HANDLE(_CreateRemoteThread(hProcess, lpThreadAttributes,
                                      dwStackSize, lpStartAddress, lpParameter,
                                      dwCreationFlags, lpThreadId))


INFINITE = ~0
WAIT_FAILED = 0xFFFFFFFF

_WaitForSingleObject = kernel32.WaitForSingleObject
_WaitForSingleObject.argtypes = [HANDLE, DWORD]
_WaitForSingleObject.restype = DWORD


def WaitForSingleObject(hHandle, dwMilliseconds):
    return DWORD(_WaitForSingleObject(hHandle, dwMilliseconds)).value


MEM_RELEASE = 0x8000

VirtualFreeEx = kernel32.VirtualFreeEx
VirtualFreeEx.argtypes = [HANDLE, LPVOID, SIZE_T, DWORD]
VirtualFreeEx.restype = BOOL

INVALID_HANDLE_VALUE = -1
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

_CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
_CreateToolhelp32Snapshot.argtypes = [DWORD, DWORD]
_CreateToolhelp32Snapshot.restype = HANDLE


def CreateToolhelp32Snapshot(dwFlags, th32ProcessID):
    return HANDLE(_CreateToolhelp32Snapshot(dwFlags, th32ProcessID))


MAX_MODULE_NAME32 = 255
MAX_PATH = 260


class MODULEENTRY32W(Structure):
    _fields_ = [('dwSize', DWORD),
                ('th32ModuleID', DWORD),
                ('th32ProcessID', DWORD),
                ('GlblcntUsage', DWORD),
                ('ProccntUsage', DWORD),
                ('modBaseAddr', POINTER(BYTE)),
                ('modBaseSize', DWORD),
                ('hModule', HMODULE),
                ('szModule', WCHAR * (MAX_MODULE_NAME32 + 1)),
                ('szExePath', WCHAR * MAX_PATH)]


LPMODULEENTRY32W = POINTER(MODULEENTRY32W)

Module32FirstW = kernel32.Module32FirstW
Module32FirstW.argtypes = [HANDLE, LPMODULEENTRY32W]
Module32FirstW.restype = BOOL

Module32NextW = kernel32.Module32NextW
Module32NextW.argtypes = [HANDLE, LPMODULEENTRY32W]
Module32NextW.restype = BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [HANDLE]
CloseHandle.restype = BOOL

STILL_ALIVE = 259

GetExitCodeThread = kernel32.GetExitCodeThread
GetExitCodeThread.argtypes = [HANDLE, LPDWORD]
GetExitCodeThread.restype = BOOL

GetExitCodeProcess = kernel32.GetExitCodeProcess
GetExitCodeProcess.argtypes = [HANDLE, LPDWORD]
GetExitCodeProcess.restype = BOOL

try:
    IsWow64Process = None
    IsWow64Process = kernel32.IsWow64Process
    IsWow64Process.argtypes = [HANDLE, POINTER(BOOL)]
    IsWow64Process.restype = BOOL
except AttributeError:
    pass

GetProcAddress32 = None

# #include <windows.h>
#
# int main() {
#   return (int)GetProcAddress(GetModuleHandle(TEXT("kernel32")),
#                              "GetProcAddress");
# }
GET_PROC_ADDRESS_32_EXE = b'eNrVU0Fr1FAQnmwX2WpbK9SLB30L24NYF9seVUihUQ8tpmhBpL\
IbN8/dxWwSsq+6omJLKTaEhR70B4gXf0AP0VPL9iLYW5EePPRgIYsVvAmCxnkv6XYLWql4cWDmm/fN\
ZN7Mey/jNxehAwCSqGEI4EMkMvxZZlB7Tr3pgaXOtbQvja2lr5fKVWI7VtHRKqSgmabFyG1KnGmTlE\
0yevUaqVg6zXZ3H87ENVQFYExK7Km7CUc7jkiH9nByLxquJO6O+4mob4BdhHMRn3gFYi6R2NuOLRBC\
sN4F+PcyhXUH9olnGa0xxA0JWrPA3mPgo+azusY09PNSPHuifdjWXS3/bZ+T7tbsNncWfSAyqMFD3O\
h1J7oTanAf/SYPvm3s+z0fdLGuBGrwA7251aR4Ra6y7vNLUNFKWHlQ4rGUzydRgzNilawr66rIVuvK\
B9RN1I9qcFxE+zzkPOQ8zk2EYTi32uUqG56yoQbfoq1+35qQpwOZybqRSU64zdkmP+h56SyHi9w83j\
69Mi+5m+47LxXmk56y3Qi+4i4eeNAIPqOnBp+EfY6lZldTaBseDYL3glwQ/0wYnjgmwxBq8wk/EM/I\
pOqjGewTBpddJam/iA4j5Y9hjqt0+bLAXh7tqysp/SVPuBXNEfZPEVlgPsZSjEaMdowsxlqMj2KcIf\
IB7v8udUxqDA/BZcpUxyqM6LpDq9VWfIHs5i6R6F0/a+O20C+RX9deQX49jn1B/I7akwY4idqPOox6\
Pn3w3J2es7ph4BI7H7f0aYNe0UzdoCMR1T5MpXqv4LA4PVewTOZYxh2bL3JVynKabefYA5sKokhZRS\
ubmlPkp0BrZf6b5m4UbHapbDDq8NUOS2sFarNcSWzsDMP/Jz8BdDoAXg=='

# #include <windows.h>
#
# typedef FARPROC(WINAPI *PGetProcAddress)(HMODULE, LPCSTR);
#
# typedef struct GetProcAddressParam {
#   FARPROC procAddress;
#   PGetProcAddress fnGetProcAddress;
#   HMODULE hModule;
#   CHAR procName[];
# } GetProcAddressParam;
#
# DWORD WINAPI ThreadProc(GetProcAddressParam *lpParameter) {
#   lpParameter->procAddress = lpParameter->fnGetProcAddress(
#       lpParameter->hModule, lpParameter->procName);
#   if (lpParameter->procAddress)
#     return TRUE;
#   return FALSE;
# }

# 0:  55                      push   ebp
# 1:  8b ec                   mov    ebp,esp
# 3:  56                      push   esi
# 4:  8b 75 08                mov    esi,DWORD PTR [ebp+0x8]
# 7:  8d 46 0c                lea    eax,[esi+0xc]
# a:  50                      push   eax
# b:  ff 76 08                push   DWORD PTR [esi+0x8]
# e:  ff 56 04                call   DWORD PTR [esi+0x4]
# 11: 33 c9                   xor    ecx,ecx
# 13: 89 06                   mov    DWORD PTR [esi],eax
# 15: 85 c0                   test   eax,eax
# 17: 5e                      pop    esi
# 18: 0f 95 c1                setne  cl
# 1b: 8b c1                   mov    eax,ecx
# 1d: 5d                      pop    ebp
# 1e: c2 04 00                ret    0x4
GET_PROC_ADDRESS_32 = b'\x55\x8B\xEC\x56\x8B\x75\x08\x8D\x46\x0C\x50\xFF\x76' \
                      b'\x08\xFF\x56\x04\x33\xC9\x89\x06\x85\xC0\x5E\x0F\x95' \
                      b'\xC1\x8B\xC1\x5D\xC2\x04\x00'

# 0:  40 53                   rex push rbx
# 2:  48 83 ec 20             sub    rsp,0x20
# 6:  48 8b d9                mov    rbx,rcx
# 9:  48 8d 51 18             lea    rdx,[rcx+0x18]
# d:  48 8b 49 10             mov    rcx,QWORD PTR [rcx+0x10]
# 11: ff 53 08                call   QWORD PTR [rbx+0x8]
# 14: 33 c9                   xor    ecx,ecx
# 16: 48 89 03                mov    QWORD PTR [rbx],rax
# 19: 48 85 c0                test   rax,rax
# 1c: 0f 95 c1                setne  cl
# 1f: 8b c1                   mov    eax,ecx
# 21: 48 83 c4 20             add    rsp,0x20
# 25: 5b                      pop    rbx
# 26: c3                      ret
GET_PROC_ADDRESS_64 = b'\x40\x53\x48\x83\xEC\x20\x48\x8B\xD9\x48\x8D\x51\x18' \
                      b'\x48\x8B\x49\x10\xFF\x53\x08\x33\xC9\x48\x89\x03\x48' \
                      b'\x85\xC0\x0F\x95\xC1\x8B\xC1\x48\x83\xC4\x20\x5B\xC3'


def resolve_module_path(path):
    path, ext = os.path.splitext(path)

    if not ext:
        ext = '.DLL'

    path = os.path.realpath(path + ext)

    if not os.path.isfile(path):
        raise FileNotFoundError('No such file: ' + path)

    return str(pathlib.Path(path).resolve())


class Process:
    class Thread:
        def __init__(self, process, start_address, param):
            self.process = process
            self.handle = CreateRemoteThread(process.handle, None, 0, cast(
                    start_address, LPTHREAD_START_ROUTINE), param, 0, None)

            if not self.handle:
                raise WinError()

        def wait(self):
            if WaitForSingleObject(self.handle, INFINITE) == WAIT_FAILED:
                raise WinError()

        def get_exit_code(self):
            exit_code = DWORD()

            if not GetExitCodeThread(self.handle, byref(exit_code)):
                raise WinError()

            return exit_code.value

        def is_still_alive(self):
            return self.get_exit_code() == STILL_ALIVE

        def close(self):
            if not CloseHandle(self.handle):
                raise WinError()

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            self.close()

    class Memory:
        def __init__(self, process, size):
            self.process = process
            self.size = size
            self.address = VirtualAllocEx(process.handle, None, size,
                                          MEM_RESERVE | MEM_COMMIT,
                                          PAGE_READWRITE)

            if not self.address:
                raise WinError()

        def free(self):
            if not VirtualFreeEx(self.process.handle, self.address, 0,
                                 MEM_RELEASE):
                raise WinError()

        def write(self, buffer, size=None):
            if size is None:
                size = self.size

            return self.process.write_memory(self.address, buffer, size)

        def read(self, buffer, size=None):
            if size is None:
                size = self.size

            return self.process.read_memory(self.address, buffer, size)

        def make_executable(self):
            old_protect = DWORD()

            if not VirtualProtectEx(self.process.handle, self.address,
                                    self.size, PAGE_EXECUTE,
                                    byref(old_protect)):
                raise WinError()

        def __enter__(self):
            return self

        def __exit__(self, type, value, traceback):
            self.free()

    class Module:
        class Proc:
            def __init__(self, module, address):
                self.module = module
                self.address = address

            def call(self, param=None):
                process = self.module.process

                with process.create_thread(self.address, param) as thread:
                    thread.wait()
                    return thread.get_exit_code()

            def __bool__(self):
                return bool(self.address)

        def __init__(self, process, handle, name, path, base_addr, base_size):
            self.process = process
            self.handle = handle
            self.name = name
            self.path = path
            self.base_addr = base_addr
            self.base_size = base_size

        def get_proc(self, name):
            global GetProcAddress32

            if self.process.bits == 32 and sys.maxsize > 2**32:
                if GetProcAddress32 is None:
                    fd, path = tempfile.mkstemp(suffix='.exe')

                    try:
                        os.write(fd, zlib.decompress(
                                b64decode(GET_PROC_ADDRESS_32_EXE,
                                          validate=True)))
                    finally:
                        os.close(fd)

                        try:
                            GetProcAddress32 = LPVOID(
                                    c_uint(subprocess.call([path])).value)
                        finally:
                            os.remove(path)

                address = GetProcAddress32
            else:
                address = GetProcAddress(GetModuleHandleW('kernel32'),
                                         b'GetProcAddress')

            _LPVOID = c_uint64 if self.process.bits == 64 else c_uint32
            _HMODULE = _LPVOID

            class GetProcAddressParam(Structure):
                _fields_ = [('procAddress', _LPVOID),
                            ('fnGetProcAddress', _LPVOID),
                            ('hModule', _HMODULE),
                            ('procName', CHAR * (len(name) + 1))]

            param = GetProcAddressParam()
            param.fnGetProcAddress = address.value
            param.hModule = self.handle.value
            param.procName = name.encode('ascii')

            if self.process.bits == 64:
                code = GET_PROC_ADDRESS_64
            else:
                code = GET_PROC_ADDRESS_32

            with self.process.alloc_memory(sizeof(param)) as memory:
                memory.write(byref(param))
                ok = self.process.execute_shellcode(code, memory.address)
                memory.read(byref(param))

            if not ok:
                raise WindowsError()

            return Process.Module.Proc(self, LPVOID(param.procAddress))

        def get_proc_address(self, name):
            return self.get_proc(name).address

        def call_proc(self, name, param=None):
            return self.get_proc(name).call(param)

        def __bool__(self):
            return bool(self.handle)

    def __init__(self, pid, auto_eject=True):
        self.id = pid
        self.handle = OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ |
                                  PROCESS_VM_WRITE | PROCESS_CREATE_THREAD |
                                  PROCESS_QUERY_INFORMATION, False, pid)
        self.injected = {}
        self.auto_eject = auto_eject

        if not self.handle:
            raise WinError()

        if IsWow64Process is None:
            self.bits = 32
        else:
            wow64 = BOOL()

            if not IsWow64Process(self.handle, byref(wow64)):
                raise WinError()

            if wow64:
                self.bits = 32
            else:
                self.bits = 64

        assert self.bits == 32 or sys.maxsize > 2**32

    def inject_module(self, path, auto_eject=None):
        path = resolve_module_path(path)
        module = self.get_module(path)

        if path in self.injected:
            if auto_eject is False:
                self.injected[path] = False

            return module

        if not module:
            buffer = create_unicode_buffer(path)
            buffer_size = sizeof(buffer)

            with self.alloc_memory(buffer_size) as memory:
                memory.write(buffer, buffer_size)

                load_library_w = self.get_module(
                        name='kernel32').get_proc('LoadLibraryW')

                load_library_w.call(memory.address)

            module = self.get_module(path)

            if not self.get_module(path):
                raise WindowsError()
        else:
            auto_eject = False

        self.injected[path] = auto_eject
        return module

    def execute_shellcode(self, code, param=None):
        with self.alloc_memory(len(code)) as memory:
            memory.write(code, len(code))
            memory.make_executable()

            with self.create_thread(memory.address, param) as thread:
                thread.wait()
                return thread.get_exit_code()

    def eject_module(self, path):
        path = resolve_module_path(path)

        if path not in self.injected:
            return False

        module = self.get_module(path)

        if module:
            free_library = self.get_module(
                    name='kernel32').get_proc('FreeLibrary')

            if not free_library.call(module.handle):
                raise WindowsError()

        del self.injected[path]
        return True

    def get_module(self, path=None, name=None):
        if path is not None:
            path = resolve_module_path(path)

        if name is not None:
            name, ext = os.path.splitext(name)

            if not ext:
                ext = '.DLL'

            name = name + ext

        snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE |
                                            TH32CS_SNAPMODULE32, self.id)

        if snapshot.value == HANDLE(INVALID_HANDLE_VALUE).value:
            raise WinError()

        module = None

        me = MODULEENTRY32W()
        me.dwSize = sizeof(me)

        ok = Module32FirstW(snapshot, byref(me))

        while ok:
            if (path is None or me.szExePath.lower() == path.lower()) and \
               (name is None or me.szModule.lower() == name.lower()):
                module = HANDLE(me.hModule)
                name = me.szModule
                path = me.szExePath
                base_addr = cast(me.modBaseAddr, LPVOID)
                base_size = me.modBaseSize
                break

            ok = Module32NextW(snapshot, byref(me))

        if not CloseHandle(snapshot):
            raise WinError()

        if module is None:
            return None

        return Process.Module(self, module, name, path, base_addr, base_size)

    def get_module_handle(self, path=None, name=None):
        return self.get_module(path=path, name=name).handle

    def write_memory(self, address, buffer, size):
        num_bytes_written = SIZE_T()

        if not WriteProcessMemory(self.handle, address, buffer,
                                  size, byref(num_bytes_written)):
            raise WinError()

        return num_bytes_written.value

    def read_memory(self, address, buffer, size):
        num_bytes_read = SIZE_T()

        if not ReadProcessMemory(self.handle, address, buffer,
                                 size, byref(num_bytes_read)):
            raise WinError()

        return num_bytes_read.value

    def create_thread(self, start_address, param=None):
        return Process.Thread(self, start_address, param)

    def alloc_memory(self, size):
        return Process.Memory(self, size)

    def get_exit_code(self):
        exit_code = DWORD()

        if not GetExitCodeProcess(self.handle, byref(exit_code)):
            raise WinError()

        return exit_code.value

    def is_still_alive(self):
        return self.get_exit_code() == STILL_ALIVE

    def close(self):
        try:
            for path, auto_eject in reversed(list(self.injected.items())):
                if auto_eject or auto_eject is None and self.auto_eject:
                    self.eject_module(path)
        finally:
            if not CloseHandle(self.handle):
                raise WinError()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
