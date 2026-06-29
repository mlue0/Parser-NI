@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================
echo   SimpleMeasure — сборка EXE
echo ============================================
echo.

:: Проверяем Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ОШИБКА] Python не найден. Установи Python 3.11+ и добавь в PATH.
    pause & exit /b 1
)

:: Устанавливаем PyInstaller если нет
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Устанавливаю PyInstaller...
    pip install pyinstaller --quiet
)

:: Устанавливаем UPX (опционально, для сжатия)
where upx >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo UPX не найден — сборка без сжатия [не критично]
)

echo.
echo Собираю SimpleMeasure.exe...
echo.

pyinstaller SimpleMeasure.spec --clean --noconfirm

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo   УСПЕХ! EXE создан: dist\SimpleMeasure.exe
    echo ============================================
    echo.
    echo Теперь запусти "Создать ярлык на рабочем столе.bat"
    echo чтобы добавить ярлык на рабочий стол.
) else (
    echo.
    echo [ОШИБКА] Сборка завершилась с ошибкой.
    echo Проверь вывод выше.
)

echo.
pause
