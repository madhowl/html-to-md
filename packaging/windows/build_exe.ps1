param(
    [ValidateSet("onefile", "onedir", "both")]
    [string]$Mode = "both"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Build = Join-Path $Root "build\windows"
$Dist = Join-Path $Root "dist"
$Payload = Join-Path $Build "payload"

Remove-Item -Path $Build -Recurse -Force -ErrorAction SilentlyContinue
$null = New-Item -ItemType Directory -Force -Path $Build, $Dist, $Payload

& uv --directory $Root sync --frozen
if ($LASTEXITCODE -ne 0) { throw "uv sync failed" }

& pwsh (Join-Path $PSScriptRoot "bundle_gtk_dlls.ps1") -Output $Payload
if ($LASTEXITCODE -ne 0) { throw "bundle_gtk_dlls.ps1 failed" }

$Version = & uv --directory $Root run python -c "from html2doc import __version__; print(__version__)"
if ($LASTEXITCODE -ne 0) { throw "version lookup failed" }
$Version = $Version.Trim()

$env:HTML2DOC_PAYLOAD_DIR = $Payload
$env:HTML2DOC_ICON = Join-Path $Root "packaging\icons\icon.ico"
$env:PATH = "$(Join-Path $Payload 'native');$env:PATH"
$env:FONTCONFIG_FILE = Join-Path $Payload "fonts\fonts.conf"
$env:FONTCONFIG_PATH = Join-Path $Payload "fonts"

function Invoke-Build([bool]$OneFile, [string]$Name) {
    $work = Join-Path $Build "work-$Name"
    $out = Join-Path $Build "dist-$Name"
    $env:HTML2DOC_ONEFILE = if ($OneFile) { "1" } else { "0" }
    & uv --directory $Root run pyinstaller (Join-Path $Root "packaging\pyinstaller.spec") `
        --noconfirm `
        --distpath $out `
        --workpath $work `
        --log-level WARN 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller $Name failed" }
    return $out
}

if ($Mode -in @("onefile", "both")) {
    $out = Invoke-Build $true "onefile"
    $exe = Join-Path $out "html2doc\html2doc.exe"
    $target = Join-Path $Dist "html2doc-$Version-windows-x86_64.exe"
    Copy-Item -Path $exe -Destination $target -Force
    & $target --version
    & $target selftest
    if ($LASTEXITCODE -ne 0) { throw "onefile selftest failed" }
    Write-Host "Готово: $target"
}

if ($Mode -in @("onedir", "both")) {
    $out = Invoke-Build $false "onedir"
    $appDir = Join-Path $out "html2doc"
    & (Join-Path $appDir "html2doc.exe") --version
    & (Join-Path $appDir "html2doc.exe") selftest
    if ($LASTEXITCODE -ne 0) { throw "onedir selftest failed" }
    $zip = Join-Path $Dist "html2doc-$Version-windows-x86_64-portable.zip"
    Compress-Archive -Path (Join-Path $appDir "*") -DestinationPath $zip -Force
    Write-Host "Готово: $zip"
}
