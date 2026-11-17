param(
    [string]$MingwRoot = "C:\msys64\mingw64",
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = "Stop"
$binDir = Join-Path $MingwRoot "bin"
if (-not (Test-Path $binDir)) {
    throw "Не найден каталог MSYS2: $binDir"
}

$nativeDir = Join-Path $Output "native"
$fontDir = Join-Path $Output "fonts"
$null = New-Item -ItemType Directory -Force -Path $nativeDir, $fontDir

Get-ChildItem -Path $binDir -Filter "*.dll" -File | Copy-Item -Destination $nativeDir -Force

$fontSource = Join-Path $MingwRoot "share\fonts"
if (Test-Path $fontSource) {
    Copy-Item -Path (Join-Path $fontSource "*") -Destination $fontDir -Recurse -Force
}

$confSource = Join-Path $MingwRoot "etc\fonts\conf.d"
if (Test-Path $confSource) {
    $confTarget = Join-Path $fontDir "conf.d"
    $null = New-Item -ItemType Directory -Force -Path $confTarget
    Copy-Item -Path (Join-Path $confSource "*") -Destination $confTarget -Recurse -Force
}

Copy-Item -Path (Join-Path $PSScriptRoot "..\fonts.conf") -Destination (Join-Path $fontDir "fonts.conf") -Force
Write-Host "Подготовлено DLL: $((Get-ChildItem -Path $nativeDir -Filter '*.dll' -File).Count)"
