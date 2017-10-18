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

static BOOL bRunning;
static HANDLE hMutex;
static WCHAR serverName[SERVER_NAME_SIZE];
static INTERNET_PORT serverPort;
static HINTERNET hSession;
static HINTERNET hConnect;

static void(WINAPI *GdiSetLastError)(DWORD dwErrCode);
static BOOL(WINAPI *NtGdiSetDeviceGammaRamp)(HDC hDC, LPVOID lpRamp);

BOOL WINAPI Hook(HDC hDC, LPVOID lpRamp) {
  BOOL bResult = FALSE;
  WORD temperature[] = {((WORD *)lpRamp)[255], ((WORD *)lpRamp)[511],
                        ((WORD *)lpRamp)[767]};

  if (WaitForSingleObject(hMutex, INFINITE) != WAIT_OBJECT_0)
    return FALSE;

  if (!bRunning || GetObjectType(hDC) != OBJ_DC) {
    if (lpRamp == NULL) {
      GdiSetLastError(ERROR_INVALID_PARAMETER);
      bResult = FALSE;
    } else {
      bResult = NtGdiSetDeviceGammaRamp(hDC, lpRamp);
    }
  } else {
    HINTERNET hRequest = NULL;

    if (hConnect) {
      double r = temperature[0] / 65535.0;
      double g = temperature[1] / 65535.0;
      double b = temperature[2] / 65535.0;

      WCHAR objectName[32];
      swprintf(objectName, 32, L"/?ct=%#.6f,%#.6f,%#.6f", r, g, b);

      hRequest = WinHttpOpenRequest(hConnect, NULL, objectName, NULL,
                                    WINHTTP_NO_REFERER,
                                    WINHTTP_DEFAULT_ACCEPT_TYPES, 0);
    }

    if (hRequest)
      bResult = WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                                   WINHTTP_NO_REQUEST_DATA, 0, 0, 0);

    if (bResult)
      WinHttpReceiveResponse(hRequest, NULL);

    if (hRequest)
      WinHttpCloseHandle(hRequest);

    bResult = TRUE;
  }

  ReleaseMutex(hMutex);
  return bResult;
}

DWORD HookStop(LPVOID lpParameter) {
  if (WaitForSingleObject(hMutex, INFINITE) != WAIT_OBJECT_0)
    return FALSE;

  if (hConnect && WinHttpCloseHandle(hConnect))
    hConnect = NULL;

  if (!hConnect && hSession && WinHttpCloseHandle(hSession))
    hSession = NULL;

  BOOL bResult = !hConnect && !hSession;
  bRunning = !bResult;
  ReleaseMutex(hMutex);
  return bResult;
}

DWORD HookStart(LPVOID lpParameter) {
  if (!HookStop(NULL))
    return FALSE;

  if (WaitForSingleObject(hMutex, INFINITE) != WAIT_OBJECT_0)
    return FALSE;

  BOOL bResult = FALSE;

  if (!hSession) {
    HookParam *param = lpParameter;

    memcpy(serverName, param->serverName, sizeof(serverName));
    serverPort = param->serverPort;

    hSession = WinHttpOpen(NULL, WINHTTP_ACCESS_TYPE_NO_PROXY,
                           WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
  }

  if (hSession)
    WinHttpSetTimeouts(hSession, 1000, 1000, 1000, 1000);

  if (hSession && !hConnect)
    hConnect = WinHttpConnect(hSession, serverName, serverPort, 0);

  bResult = hConnect != NULL;
  bRunning = bResult;
  ReleaseMutex(hMutex);
  return bResult;
}

BOOL APIENTRY DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {
  switch (fdwReason) {
  case DLL_PROCESS_ATTACH:
    GdiSetLastError = (void(WINAPI *)(DWORD))GetProcAddress(
        GetModuleHandle(TEXT("gdi32")), "GdiSetLastError");
    NtGdiSetDeviceGammaRamp = (BOOL(WINAPI *)(HDC, LPVOID))GetProcAddress(
        GetModuleHandle(TEXT("win32u")), "NtGdiSetDeviceGammaRamp");

    bRunning = FALSE;
    hMutex = CreateMutex(NULL, FALSE, NULL);

    if (!hMutex)
      return FALSE;

    memset(serverName, 0, sizeof(serverName));
    serverPort = 0;
    hSession = NULL;
    hConnect = NULL;
    break;
  case DLL_PROCESS_DETACH:
    HookStop(NULL);
    CloseHandle(hMutex);
    break;
  }

  return TRUE;
}
