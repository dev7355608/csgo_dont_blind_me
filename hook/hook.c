#include <stdlib.h>
#include <wchar.h>
#include <windows.h>
#include <winhttp.h>

#pragma comment(lib, "winhttp.lib")

#define SERVER_NAME_SIZE 16

typedef struct HookParam {
  WCHAR serverName[SERVER_NAME_SIZE];
  INTERNET_PORT serverPort;
} HookParam;

static HANDLE mutex;
static WCHAR serverName[SERVER_NAME_SIZE];
static INTERNET_PORT serverPort;
static HINTERNET hSession;
static HINTERNET hConnect;

BOOL WINAPI Hook(HDC hDC, LPVOID lpRamp) {
  if (GetObjectType(hDC) != OBJ_DC)
    return SetDeviceGammaRamp(hDC, lpRamp);

  if (WaitForSingleObject(mutex, INFINITE) != WAIT_OBJECT_0)
    return TRUE;

  ULONGLONG start = GetTickCount64();

  if (!hConnect && hSession)
    hConnect = WinHttpConnect(hSession, serverName, serverPort, 0);

  HINTERNET hRequest = NULL;

  if (hConnect) {
    double r = ((WORD *)lpRamp)[255] / 65535.0;
    double g = ((WORD *)lpRamp)[511] / 65535.0;
    double b = ((WORD *)lpRamp)[767] / 65535.0;

    WCHAR objectName[32];
    swprintf(objectName, 32, L"/?ct=%#.6f,%#.6f,%#.6f", r, g, b);

    hRequest =
        WinHttpOpenRequest(hConnect, NULL, objectName, NULL, WINHTTP_NO_REFERER,
                           WINHTTP_DEFAULT_ACCEPT_TYPES, 0);
  }

  BOOL bResults = FALSE;

  if (hRequest)
    bResults = WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                                  WINHTTP_NO_REQUEST_DATA, 0, 0, 0);

  if (bResults)
    WinHttpReceiveResponse(hRequest, NULL);

  if (hRequest)
    WinHttpCloseHandle(hRequest);

  ULONGLONG delta = GetTickCount64() - start;

  if (delta < 5)
    Sleep((DWORD)(5 - delta));

  ReleaseMutex(mutex);
  return TRUE;
}

DWORD HookStop(LPVOID lpParameter) {
  if (WaitForSingleObject(mutex, INFINITE) != WAIT_OBJECT_0)
    return FALSE;

  if (hConnect && WinHttpCloseHandle(hConnect))
    hConnect = NULL;

  if (!hConnect && hSession && WinHttpCloseHandle(hSession))
    hSession = NULL;

  BOOL result = !hConnect && !hSession;

  ReleaseMutex(mutex);
  return result;
}

DWORD HookStart(LPVOID lpParameter) {
  if (!HookStop(NULL))
    return FALSE;

  if (WaitForSingleObject(mutex, INFINITE) != WAIT_OBJECT_0)
    return FALSE;

  BOOL result = FALSE;

  if (!hSession) {
    HookParam *param = lpParameter;

    memcpy(serverName, param->serverName, sizeof(serverName));
    serverPort = param->serverPort;

    hSession = WinHttpOpen(NULL, WINHTTP_ACCESS_TYPE_NO_PROXY,
                           WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);

    if (hSession) {
        WinHttpSetTimeouts(hSession, 1000, 250, 50, 50);
    }

    result = hSession != NULL;
  }

  ReleaseMutex(mutex);
  return result;
}

BOOL APIENTRY DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
  switch (fdwReason) {
  case DLL_PROCESS_ATTACH:
    mutex = CreateMutex(NULL, FALSE, NULL);

    if (!mutex)
      return FALSE;

    memset(serverName, 0, sizeof(serverName));
    serverPort = 0;
    hSession = NULL;
    hConnect = NULL;
    break;
  case DLL_PROCESS_DETACH:
    HookStop(NULL);
    CloseHandle(mutex);
    break;
  }

  return TRUE;
}
