#include <stdint.h>
typedef uint16_t WCHAR; typedef uint32_t DWORD; typedef int32_t BOOL; typedef void* HANDLE; typedef void* HMODULE; typedef void* FARPROC; typedef uint16_t WORD; typedef uint8_t BYTE; typedef int32_t NTSTATUS; typedef uint32_t ULONG; typedef uint16_t USHORT; typedef char CHAR;
#define INFINITE 0xFFFFFFFFu
#define MB_OK 0u
#define MB_ICONERROR 0x10u
#define MB_ICONINFORMATION 0x40u

typedef struct { USHORT Length; USHORT MaximumLength; WCHAR* Buffer; } UNICODE_STRING;
typedef struct { USHORT Length; USHORT MaximumLength; CHAR* Buffer; } ANSI_STRING;
typedef struct _LIST_ENTRY { struct _LIST_ENTRY* Flink; struct _LIST_ENTRY* Blink; } LIST_ENTRY;
typedef struct { DWORD cb; WCHAR* lpReserved; WCHAR* lpDesktop; WCHAR* lpTitle; DWORD dwX; DWORD dwY; DWORD dwXSize; DWORD dwYSize; DWORD dwXCountChars; DWORD dwYCountChars; DWORD dwFillAttribute; DWORD dwFlags; WORD wShowWindow; WORD cbReserved2; BYTE* lpReserved2; HANDLE hStdInput; HANDLE hStdOutput; HANDLE hStdError; } STARTUPINFOW;
typedef struct { HANDLE hProcess; HANDLE hThread; DWORD dwProcessId; DWORD dwThreadId; } PROCESS_INFORMATION;

typedef NTSTATUS (*LdrLoadDll_t)(WCHAR*,ULONG*,UNICODE_STRING*,HMODULE*);
typedef NTSTATUS (*LdrGetProcedureAddress_t)(HMODULE,ANSI_STRING*,ULONG,FARPROC*);
typedef DWORD (*GetModuleFileNameW_t)(HMODULE,WCHAR*,DWORD);
typedef BOOL (*CreateProcessW_t)(const WCHAR*,WCHAR*,void*,void*,BOOL,DWORD,void*,const WCHAR*,STARTUPINFOW*,PROCESS_INFORMATION*);
typedef BOOL (*SetEnvironmentVariableW_t)(const WCHAR*,const WCHAR*);
typedef DWORD (*WaitForSingleObject_t)(HANDLE,DWORD);
typedef BOOL (*GetExitCodeProcess_t)(HANDLE,DWORD*);
typedef BOOL (*CloseHandle_t)(HANDLE);
typedef void (*ExitProcess_t)(DWORD);
typedef int (*MessageBoxW_t)(void*,const WCHAR*,const WCHAR*,unsigned int);

static WCHAR G_PATH[2048], G_SCRIPT[8192], G_CMD[16384], G_TITLE[96], G_TMP[512];

static void* get_peb(void){ void* p; __asm__("movq %%gs:0x60, %0" : "=r"(p)); return p; }
static int lowerw(WCHAR c){ return (c>='A'&&c<='Z')?c+32:c; }
static int wnameeq(WCHAR* b, WORD lenBytes, const char* ascii){ unsigned n=lenBytes/2,i=0; for(;ascii[i]&&i<n;i++) if(lowerw(b[i])!=(unsigned char)ascii[i]) return 0; return ascii[i]==0 && i==n; }
static int streq(const char*a,const char*b){ while(*a&&*b){if(*a++!=*b++)return 0;}return *a==*b; }
static unsigned alen(const char*s){unsigned n=0;while(s[n])n++;return n;}
static unsigned wlen(const WCHAR*s){unsigned n=0;while(s[n])n++;return n;}
static void wcopy(WCHAR*d,const WCHAR*s){while((*d++=*s++));}
static void wcat(WCHAR*d,const WCHAR*s){d+=wlen(d);wcopy(d,s);}
static void acopyw(WCHAR*d,const char*s){while(*s)*d++=(unsigned char)*s++;*d=0;}
static void* module_base(const char* name){ uint8_t* peb=(uint8_t*)get_peb(); uint8_t* ldr=*(uint8_t**)(peb+0x18); LIST_ENTRY* head=(LIST_ENTRY*)(ldr+0x20); LIST_ENTRY* cur=head->Flink; while(cur!=head){uint8_t* ent=(uint8_t*)cur-0x10;void* base=*(void**)(ent+0x30);UNICODE_STRING* us=(UNICODE_STRING*)(ent+0x58);if(us->Buffer&&wnameeq(us->Buffer,us->Length,name))return base;cur=cur->Flink;}return 0; }
static void* raw_export(void* base,const char* name){ uint8_t*b=(uint8_t*)base;uint32_t lfanew=*(uint32_t*)(b+0x3c);uint8_t*nt=b+lfanew;uint32_t expRva=*(uint32_t*)(nt+24+112);if(!expRva)return 0;uint8_t*e=b+expRva;uint32_t nn=*(uint32_t*)(e+24),funcs=*(uint32_t*)(e+28),names=*(uint32_t*)(e+32),ords=*(uint32_t*)(e+36);uint32_t*na=(uint32_t*)(b+names),*fa=(uint32_t*)(b+funcs);uint16_t*oa=(uint16_t*)(b+ords);for(uint32_t i=0;i<nn;i++){const char*n=(const char*)(b+na[i]);if(streq(n,name))return b+fa[oa[i]];}return 0; }
static FARPROC ldr_get(LdrGetProcedureAddress_t f, HMODULE m, const char* name){ ANSI_STRING a; a.Length=(USHORT)alen(name);a.MaximumLength=a.Length;a.Buffer=(CHAR*)name;FARPROC p=0; if(f(m,&a,0,&p)<0)return 0;return p; }
static HMODULE ldr_load(LdrLoadDll_t f,const char* name){ WCHAR* w=G_TMP;acopyw(w,name);UNICODE_STRING u;u.Length=(USHORT)(wlen(w)*2);u.MaximumLength=u.Length+2;u.Buffer=w;HMODULE m=0;if(f(0,0,&u,&m)<0)return 0;return m; }

#ifndef SCRIPT_NAME
#define SCRIPT_NAME "install.ps1"
#endif
#ifndef APP_TITLE
#define APP_TITLE "SONICRAFT AI Strings"
#endif

void entry(void){
 HMODULE ntdll=(HMODULE)module_base("ntdll.dll"); if(!ntdll)return;
 LdrLoadDll_t LdrLoadDll=(LdrLoadDll_t)raw_export(ntdll,"LdrLoadDll"); LdrGetProcedureAddress_t LdrGetProcedureAddress=(LdrGetProcedureAddress_t)raw_export(ntdll,"LdrGetProcedureAddress"); if(!LdrLoadDll||!LdrGetProcedureAddress)return;
 HMODULE k=(HMODULE)module_base("kernel32.dll"); if(!k) k=ldr_load(LdrLoadDll,"kernel32.dll"); if(!k)return;
 GetModuleFileNameW_t GetModuleFileNameW=(GetModuleFileNameW_t)ldr_get(LdrGetProcedureAddress,k,"GetModuleFileNameW");
 CreateProcessW_t CreateProcessW=(CreateProcessW_t)ldr_get(LdrGetProcedureAddress,k,"CreateProcessW");
 SetEnvironmentVariableW_t SetEnvironmentVariableW=(SetEnvironmentVariableW_t)ldr_get(LdrGetProcedureAddress,k,"SetEnvironmentVariableW");
 WaitForSingleObject_t WaitForSingleObject=(WaitForSingleObject_t)ldr_get(LdrGetProcedureAddress,k,"WaitForSingleObject");
 GetExitCodeProcess_t GetExitCodeProcess=(GetExitCodeProcess_t)ldr_get(LdrGetProcedureAddress,k,"GetExitCodeProcess");
 CloseHandle_t CloseHandle=(CloseHandle_t)ldr_get(LdrGetProcedureAddress,k,"CloseHandle");
 ExitProcess_t ExitProcess=(ExitProcess_t)ldr_get(LdrGetProcedureAddress,k,"ExitProcess");
 HMODULE u=ldr_load(LdrLoadDll,"user32.dll"); MessageBoxW_t MessageBoxW=u?(MessageBoxW_t)ldr_get(LdrGetProcedureAddress,u,"MessageBoxW"):0;
 WCHAR* title=G_TITLE;acopyw(title,APP_TITLE);
 if(!GetModuleFileNameW||!CreateProcessW||!SetEnvironmentVariableW||!WaitForSingleObject||!GetExitCodeProcess||!CloseHandle){if(ExitProcess)ExitProcess(90);return;}
 WCHAR* path=G_PATH;if(!GetModuleFileNameW(0,path,2048)){if(MessageBoxW){WCHAR*m=G_TMP;acopyw(m,"Cannot resolve application path.");MessageBoxW(0,m,title,MB_OK|MB_ICONERROR);}if(ExitProcess)ExitProcess(91);return;}
 WCHAR* envn=G_TMP;acopyw(envn,"SONICRAFT_SETUP_EXE");if(!SetEnvironmentVariableW(envn,path)){if(MessageBoxW){WCHAR*m=G_SCRIPT;acopyw(m,"Could not pass the installer path to the extraction process.");MessageBoxW(0,m,title,MB_OK|MB_ICONERROR);}if(ExitProcess)ExitProcess(94);return;}
 int last=-1;for(int i=0;path[i];i++)if(path[i]=='\\'||path[i]=='/')last=i;if(last<0){if(ExitProcess)ExitProcess(92);return;}path[last+1]=0;
 WCHAR*cmd=G_CMD;acopyw(cmd,"powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand ");WCHAR*encw=G_SCRIPT;acopyw(encw,"JABFAHIAcgBvAHIAQQBjAHQAaQBvAG4AUAByAGUAZgBlAHIAZQBuAGMAZQA9ACcAUwB0AG8AcAAnAAoAJABsAG8AZwA9AEoAbwBpAG4ALQBQAGEAdABoACAAJABlAG4AdgA6AFQARQBNAFAAIAAnAFMATwBOAEkAQwBSAEEARgBUAF8AQQBJAF8AUwB0AHIAaQBuAGcAcwBfAFMAZQB0AHUAcABfAGIAbwBvAHQAcwB0AHIAYQBwAC4AbABvAGcAJwAKAHQAcgB5ACAAewAKACAAIAAiAFsAJAAoAEcAZQB0AC0ARABhAHQAZQAgAC0ARgBvAHIAbQBhAHQAIABzACkAXQAgAEIAbwBvAHQAcwB0AHIAYQBwACAAcwB0AGEAcgB0AGUAZAAuACIAIAB8ACAAUwBlAHQALQBDAG8AbgB0AGUAbgB0ACAALQBFAG4AYwBvAGQAaQBuAGcAIABVAFQARgA4ACAALQBQAGEAdABoACAAJABsAG8AZwAKACAAIAAkAGUAeABlAD0AJABlAG4AdgA6AFMATwBOAEkAQwBSAEEARgBUAF8AUwBFAFQAVQBQAF8ARQBYAEUACgAgACAAaQBmACgAWwBzAHQAcgBpAG4AZwBdADoAOgBJAHMATgB1AGwAbABPAHIAVwBoAGkAdABlAFMAcABhAGMAZQAoACQAZQB4AGUAKQAgAC0AbwByACAALQBuAG8AdAAgACgAVABlAHMAdAAtAFAAYQB0AGgAIAAtAEwAaQB0AGUAcgBhAGwAUABhAHQAaAAgACQAZQB4AGUAKQApACAAewAgAHQAaAByAG8AdwAgACIASQBuAHMAdABhAGwAbABlAHIAIABzAGUAbABmACAAcABhAHQAaAAgAGkAcwAgAHUAbgBhAHYAYQBpAGwAYQBiAGwAZQA6ACAAJABlAHgAZQAiACAAfQAKACAAIAAiAFMAZQBsAGYAPQAkAGUAeABlACIAIAB8ACAAQQBkAGQALQBDAG8AbgB0AGUAbgB0ACAALQBFAG4AYwBvAGQAaQBuAGcAIABVAFQARgA4ACAALQBQAGEAdABoACAAJABsAG8AZwAKACAAIAAkAGIAPQBbAEkATwAuAEYAaQBsAGUAXQA6ADoAUgBlAGEAZABBAGwAbABCAHkAdABlAHMAKAAkAGUAeABlACkACgAgACAAJABtAD0AWwBUAGUAeAB0AC4ARQBuAGMAbwBkAGkAbgBnAF0AOgA6AEEAUwBDAEkASQAuAEcAZQB0AEIAeQB0AGUAcwAoACcAUwBDAF8AUABBAFkATABPAEEARABfAFoASQBQAF8AVgAxADIAMABfAFIAQwAyAF8ASABGADEAXwA3AEYAMwBDADEAOQBBADIAJwApAAoAIAAgACQAaQBkAHgAPQAtADEACgAgACAAZgBvAHIAKAAkAGkAPQAkAGIALgBMAGUAbgBnAHQAaAAtACQAbQAuAEwAZQBuAGcAdABoADsAJABpACAALQBnAGUAIAAwADsAJABpAC0ALQApACAAewAKACAAIAAgACAAJABvAGsAPQAkAHQAcgB1AGUACgAgACAAIAAgAGYAbwByACgAJABqAD0AMAA7ACQAagAgAC0AbAB0ACAAJABtAC4ATABlAG4AZwB0AGgAOwAkAGoAKwArACkAIAB7ACAAaQBmACgAJABiAFsAJABpACsAJABqAF0AIAAtAG4AZQAgACQAbQBbACQAagBdACkAIAB7ACQAbwBrAD0AJABmAGEAbABzAGUAOwBiAHIAZQBhAGsAfQAgAH0ACgAgACAAIAAgAGkAZgAoACQAbwBrACkAIAB7ACQAaQBkAHgAPQAkAGkAOwBiAHIAZQBhAGsAfQAKACAAIAB9AAoAIAAgAGkAZgAoACQAaQBkAHgAIAAtAGwAdAAgADAAKQAgAHsAIAB0AGgAcgBvAHcAIAAnAEUAbQBiAGUAZABkAGUAZAAgAGkAbgBzAHQAYQBsAGwAZQByACAAcABhAHkAbABvAGEAZAAgAHcAYQBzACAAbgBvAHQAIABmAG8AdQBuAGQALgAnACAAfQAKACAAIAAkAG4APQAkAGIALgBMAGUAbgBnAHQAaAAtACQAaQBkAHgALQAkAG0ALgBMAGUAbgBnAHQAaAAKACAAIABpAGYAKAAkAG4AIAAtAGwAdAAgADQAKQAgAHsAIAB0AGgAcgBvAHcAIAAnAEUAbQBiAGUAZABkAGUAZAAgAGkAbgBzAHQAYQBsAGwAZQByACAAcABhAHkAbABvAGEAZAAgAGkAcwAgAGUAbQBwAHQAeQAuACcAIAB9AAoAIAAgACQAdABtAHAAPQBKAG8AaQBuAC0AUABhAHQAaAAgACQAZQBuAHYAOgBUAEUATQBQACAAKAAnAFMATwBOAEkAQwBSAEEARgBUAF8AQQBJAF8AUwB0AHIAaQBuAGcAcwBfAFMAZQB0AHUAcABfACcAKwAkAFAASQBEACsAJwBfACcAKwBbAEcAdQBpAGQAXQA6ADoATgBlAHcARwB1AGkAZAAoACkALgBUAG8AUwB0AHIAaQBuAGcAKAAnAE4AJwApACkACgAgACAAJAB6AGkAcAA9ACQAdABtAHAAKwAnAC4AegBpAHAAJwAKACAAIABOAGUAdwAtAEkAdABlAG0AIAAtAEkAdABlAG0AVAB5AHAAZQAgAEQAaQByAGUAYwB0AG8AcgB5ACAALQBGAG8AcgBjAGUAIAAtAFAAYQB0AGgAIAAkAHQAbQBwACAAfAAgAE8AdQB0AC0ATgB1AGwAbAAKACAAIAAkAHAAYQB5AGwAbwBhAGQAPQBOAGUAdwAtAE8AYgBqAGUAYwB0ACAAYgB5AHQAZQBbAF0AIAAkAG4ACgAgACAAWwBBAHIAcgBhAHkAXQA6ADoAQwBvAHAAeQAoACQAYgAsACQAaQBkAHgAKwAkAG0ALgBMAGUAbgBnAHQAaAAsACQAcABhAHkAbABvAGEAZAAsADAALAAkAG4AKQAKACAAIABbAEkATwAuAEYAaQBsAGUAXQA6ADoAVwByAGkAdABlAEEAbABsAEIAeQB0AGUAcwAoACQAegBpAHAALAAkAHAAYQB5AGwAbwBhAGQAKQAKACAAIAAiAFAAYQB5AGwAbwBhAGQAIABiAHkAdABlAHMAPQAkAG4AIABUAGUAbQBwAD0AJAB0AG0AcAAiACAAfAAgAEEAZABkAC0AQwBvAG4AdABlAG4AdAAgAC0ARQBuAGMAbwBkAGkAbgBnACAAVQBUAEYAOAAgAC0AUABhAHQAaAAgACQAbABvAGcACgAgACAARQB4AHAAYQBuAGQALQBBAHIAYwBoAGkAdgBlACAALQBMAGkAdABlAHIAYQBsAFAAYQB0AGgAIAAkAHoAaQBwACAALQBEAGUAcwB0AGkAbgBhAHQAaQBvAG4AUABhAHQAaAAgACQAdABtAHAAIAAtAEYAbwByAGMAZQAKACAAIAAkAGkAbgBzAHQAYQBsAGwAZQByAD0ASgBvAGkAbgAtAFAAYQB0AGgAIAAkAHQAbQBwACAAJwBpAG4AcwB0AGEAbABsAC4AcABzADEAJwAKACAAIABpAGYAKAAtAG4AbwB0ACAAKABUAGUAcwB0AC0AUABhAHQAaAAgAC0ATABpAHQAZQByAGEAbABQAGEAdABoACAAJABpAG4AcwB0AGEAbABsAGUAcgApACkAIAB7ACAAdABoAHIAbwB3ACAAIgBpAG4AcwB0AGEAbABsAC4AcABzADEAIABtAGkAcwBzAGkAbgBnACAAYQBmAHQAZQByACAAZQB4AHQAcgBhAGMAdABpAG8AbgA6ACAAJABpAG4AcwB0AGEAbABsAGUAcgAiACAAfQAKACAAIAAkAHAAcwBFAHgAZQA9AEoAbwBpAG4ALQBQAGEAdABoACAAJABlAG4AdgA6AFMAeQBzAHQAZQBtAFIAbwBvAHQAIAAnAFMAeQBzAHQAZQBtADMAMgBcAFcAaQBuAGQAbwB3AHMAUABvAHcAZQByAFMAaABlAGwAbABcAHYAMQAuADAAXABwAG8AdwBlAHIAcwBoAGUAbABsAC4AZQB4AGUAJwAKACAAIABpAGYAKAAtAG4AbwB0ACAAKABUAGUAcwB0AC0AUABhAHQAaAAgAC0ATABpAHQAZQByAGEAbABQAGEAdABoACAAJABwAHMARQB4AGUAKQApACAAewAkAHAAcwBFAHgAZQA9ACcAcABvAHcAZQByAHMAaABlAGwAbAAuAGUAeABlACcAfQAKACAAIAAiAEwAYQB1AG4AYwBoAGkAbgBnACAAdwBpAHoAYQByAGQAPQAkAGkAbgBzAHQAYQBsAGwAZQByACIAIAB8ACAAQQBkAGQALQBDAG8AbgB0AGUAbgB0ACAALQBFAG4AYwBvAGQAaQBuAGcAIABVAFQARgA4ACAALQBQAGEAdABoACAAJABsAG8AZwAKACAAIAAmACAAJABwAHMARQB4AGUAIAAtAFMAVABBACAALQBOAG8ATABvAGcAbwAgAC0ATgBvAFAAcgBvAGYAaQBsAGUAIAAtAEUAeABlAGMAdQB0AGkAbwBuAFAAbwBsAGkAYwB5ACAAQgB5AHAAYQBzAHMAIAAtAEYAaQBsAGUAIAAkAGkAbgBzAHQAYQBsAGwAZQByAAoAIAAgACQAYwA9ACQATABBAFMAVABFAFgASQBUAEMATwBEAEUACgAgACAAIgBXAGkAegBhAHIAZAAgAGUAeABpAHQAIABjAG8AZABlAD0AJABjACIAIAB8ACAAQQBkAGQALQBDAG8AbgB0AGUAbgB0ACAALQBFAG4AYwBvAGQAaQBuAGcAIABVAFQARgA4ACAALQBQAGEAdABoACAAJABsAG8AZwAKACAAIABSAGUAbQBvAHYAZQAtAEkAdABlAG0AIAAtAEYAbwByAGMAZQAgACQAegBpAHAAIAAtAEUAcgByAG8AcgBBAGMAdABpAG8AbgAgAFMAaQBsAGUAbgB0AGwAeQBDAG8AbgB0AGkAbgB1AGUACgAgACAAaQBmACgAJABjACAALQBlAHEAIAAwACkAIAB7ACAAUgBlAG0AbwB2AGUALQBJAHQAZQBtACAALQBSAGUAYwB1AHIAcwBlACAALQBGAG8AcgBjAGUAIAAkAHQAbQBwACAALQBFAHIAcgBvAHIAQQBjAHQAaQBvAG4AIABTAGkAbABlAG4AdABsAHkAQwBvAG4AdABpAG4AdQBlACAAfQAKACAAIABlAHgAaQB0ACAAJABjAAoAfQAgAGMAYQB0AGMAaAAgAHsACgAgACAAKAAiAFsAJAAoAEcAZQB0AC0ARABhAHQAZQAgAC0ARgBvAHIAbQBhAHQAIABzACkAXQAgAEYAQQBUAEEATAA6ACAAIgArACQAXwAuAEUAeABjAGUAcAB0AGkAbwBuAC4ATQBlAHMAcwBhAGcAZQArACIAYAByAGAAbgAiACsAKAAkAF8AfABPAHUAdAAtAFMAdAByAGkAbgBnACkAKQAgAHwAIABBAGQAZAAtAEMAbwBuAHQAZQBuAHQAIAAtAEUAbgBjAG8AZABpAG4AZwAgAFUAVABGADgAIAAtAFAAYQB0AGgAIAAkAGwAbwBnAAoAIAAgAGUAeABpAHQAIAA5ADcACgB9AAoA");wcat(cmd,encw);
 STARTUPINFOW si={0};si.cb=sizeof(si);PROCESS_INFORMATION pi={0};BOOL ok=CreateProcessW(0,cmd,0,0,0,0,0,path,&si,&pi);
 if(!ok){if(MessageBoxW){WCHAR*m=G_TMP;acopyw(m,"Could not start the SONICRAFT installer engine. A diagnostic log may be available in your TEMP folder.");MessageBoxW(0,m,title,MB_OK|MB_ICONERROR);}if(ExitProcess)ExitProcess(93);return;}
 WaitForSingleObject(pi.hProcess,INFINITE);DWORD code=1;GetExitCodeProcess(pi.hProcess,&code);CloseHandle(pi.hThread);CloseHandle(pi.hProcess);
 if(MessageBoxW&&code!=0){WCHAR*m=G_TMP;acopyw(m,"SONICRAFT Setup could not complete. See %TEMP%\\SONICRAFT_AI_Strings_Setup_bootstrap.log for details.");MessageBoxW(0,m,title,MB_OK|MB_ICONERROR);}if(ExitProcess)ExitProcess(code);return;
}
