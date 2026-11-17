param(
    [string]$MingwRoot = "",
    [Parameter(Mandatory = $true)]
    [string]$Output
)

$ErrorActionPreference = "Stop"

function Resolve-MingwRoot([string]$Root) {
    $candidates = @()
    if ($Root) {
        $candidates += $Root
    }

    $pacman = Get-Command pacman.exe -ErrorAction SilentlyContinue
    if ($pacman) {
        $msysRoot = Split-Path (Split-Path $pacman.Source -Parent) -Parent
        $candidates += (Join-Path $msysRoot "mingw64")
    }

    if ($env:SystemDrive) {
        $candidates += (Join-Path $env:SystemDrive "msys64\mingw64")
    }
    if ($env:RUNNER_TEMP) {
        $candidates += (Join-Path $env:RUNNER_TEMP "setup-msys2\msys64\mingw64")
    }

    foreach ($candidate in $candidates) {
        if ((Test-Path $candidate) -and (Test-Path (Join-Path $candidate "bin"))) {
            return $candidate
        }
    }
    throw "Не найден каталог MSYS2 mingw64. Проверенные пути: $($candidates -join ', ')"
}

$MingwRoot = Resolve-MingwRoot $MingwRoot
$binDir = Join-Path $MingwRoot "bin"
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
Write-Host "MSYS2: $MingwRoot"
Write-Host "Подготовлено DLL: $((Get-ChildItem -Path $nativeDir -Filter '*.dll' -File).Count)"
