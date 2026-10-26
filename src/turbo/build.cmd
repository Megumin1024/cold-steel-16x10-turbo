@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x86
if errorlevel 1 exit /b 1
if not exist build mkdir build
cl /nologo /MT /O2 /EHsc /std:c++17 /utf-8 /Fo"build\test_turbo.obj" /Fe"build\test_turbo.exe" test_turbo.cpp
if errorlevel 1 exit /b 1
build\test_turbo.exe
if errorlevel 1 exit /b 1
cl /nologo /LD /MT /O2 /Oy- /EHsc /std:c++17 /utf-8 /D_CRT_SECURE_NO_WARNINGS /Fo"build\turbo_toggle.obj" /Fe"build\turbo_toggle.dll" turbo_toggle.cpp /link /MACHINE:X86 /DEF:turbo_toggle.def /MAP:build\turbo_toggle.map kernel32.lib
exit /b %errorlevel%

