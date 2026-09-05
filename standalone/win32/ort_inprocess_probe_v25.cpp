#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <iostream>
#include <string>
using OrtGetApiBaseFn = const void* (__cdecl*)();
int wmain(int argc,wchar_t**argv){
    std::wstring dll=L"onnxruntime.dll";if(argc>1)dll=argv[1];HMODULE h=LoadLibraryW(dll.c_str());if(!h){std::wcerr<<L"LoadLibrary failed: "<<dll<<L"\n";return 3;}
    auto p=reinterpret_cast<OrtGetApiBaseFn>(GetProcAddress(h,"OrtGetApiBase"));if(!p){std::cerr<<"OrtGetApiBase missing\n";FreeLibrary(h);return 4;}
    const void* base=p();if(!base){std::cerr<<"OrtGetApiBase returned null\n";FreeLibrary(h);return 5;}
    std::cout<<"v2.5 INPROCESS ORT LOADER PASS python=0 torch=0\n";FreeLibrary(h);return 0;
}
#endif
