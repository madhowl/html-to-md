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
    if ($env:MSYS2_LOCATION) {
        $candidates += $env:MSYS2_LOCATION
    }

    $pacman = Get-Command pacman.exe -ErrorAction SilentlyContinue
    if ($pacman) {
        $pacmanDir = Split-Path $pacman.Source -Parent
        $candidates += (Resolve-Path (Join-Path $pacmanDir "..\..")).Path
    }

    if ($env:SystemDrive) {
        $candidates += (Join-Path $env:SystemDrive "msys64")
    }
    if ($env:RUNNER_TEMP) {
        $candidates += (Join-Path $env:RUNNER_TEMP "msys64")
        $candidates += (Join-Path $env:RUNNER_TEMP "setup-msys2\msys64")
    }

    $checked = @()
    foreach ($candidate in $candidates) {
        $mingwRoot = if ((Split-Path $candidate -Leaf) -eq "mingw64") { $candidate } else { Join-Path $candidate "mingw64" }
        $binDir = Join-Path $mingwRoot "bin"
        if (-not (Test-Path $binDir)) {
            $checked += "$mingwRoot (нет bin)"
            continue
        }

        $dllCount = @(Get-ChildItem -Path $binDir -Filter "*.dll" -File).Count
        if ($dllCount -gt 0) {
            return $mingwRoot
        }
        $checked += "$mingwRoot (нет DLL)"
    }
    $searchRoots = @()
    foreach ($candidate in $candidates) {
        $root = if ((Split-Path $candidate -Leaf) -eq "mingw64") { Split-Path $candidate -Parent } else { $candidate }
        if ((Test-Path $root) -and ($searchRoots -notcontains $root)) {
            $searchRoots += $root
        }
    }

    $libgobject = Get-ChildItem -Path $searchRoots -Filter "libgobject-2.0-0.dll" -File -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($libgobject) {
        return Split-Path $libgobject.DirectoryName -Parent
    }

    throw "Не найден каталог MSYS2 mingw64 с DLL. Проверенные пути: $($checked -join ', ')"
}

$MingwRoot = Resolve-MingwRoot $MingwRoot
$binDir = Join-Path $MingwRoot "bin"
$nativeDir = Join-Path $Output "native"
$fontDir = Join-Path $Output "fonts"
$null = New-Item -ItemType Directory -Force -Path $nativeDir, $fontDir

$dlls = @(Get-ChildItem -Path $binDir -Filter "*.dll" -File)
if ($dlls.Count -eq 0) {
    throw "В каталоге $binDir нет DLL"
}
$dlls | Copy-Item -Destination $nativeDir -Force

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
