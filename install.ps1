$ErrorActionPreference = "Stop"
$Repository = "git+https://github.com/abhishek764/devsweep"

$pythonCommand = Get-Command py -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
}
if ($null -eq $pythonCommand) {
    Write-Error "devsweep requires Python 3.9 or newer. Install Python first."
    exit 1
}

$python = $pythonCommand.Source
$versionOk = $true
try {
    & $python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
} catch {
    $versionOk = $false
}
if (-not $versionOk) {
    Write-Error "devsweep requires Python 3.9 or newer."
    exit 1
}

if (Get-Command pipx -ErrorAction SilentlyContinue) {
    & pipx install $Repository
} elseif (Get-Command uv -ErrorAction SilentlyContinue) {
    & uv tool install $Repository
} else {
    & $python -m pip install --user $Repository
}

$userScripts = Join-Path $env:APPDATA "Python\Scripts"
$pathEntries = $env:Path -split [IO.Path]::PathSeparator
if (-not ($pathEntries -contains $userScripts)) {
    Write-Warning "Your Python user Scripts directory may not be on PATH. Restart PowerShell or add it manually."
}
Write-Output "Installed devsweep. Try: devsweep scan ."
