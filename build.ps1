$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot 'build/cache'
$payloadPath = Join-Path $PSScriptRoot 'payload'
$licensePath = Join-Path $PSScriptRoot 'licenses'
python -m PyInstaller --noconfirm --onefile --windowed --name ColdSteel-16x10-Turbo-v1.0.0 --add-data "$payloadPath;payload" --add-data "$licensePath;licenses" --paths src --distpath dist --workpath build --specpath build src/installer.py
if ($LASTEXITCODE -ne 0) { throw '安装工具打包失败' }
