# SPDX-License-Identifier: GPL-3.0-or-later
# irm https://raw.githubusercontent.com/nextcode4u/gloam-shell-theme-directory/main/splash.ps1 | iex
[CmdletBinding()]
param(
    [string]$Workspace,
    [string]$Python,
    [string]$CacheDirectory,
    [string]$SourceDirectory,
    [switch]$Offline,
    [switch]$NoLaunch,
    [switch]$LibraryOnly
)

function Get-SplashHash([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose(); $stream.Dispose() }
}

function Test-SplashPackage([string]$Folder) {
    $manifestPath = Join-Path $Folder 'tools/splash-downloads.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf) -or (Get-Item -LiteralPath $manifestPath).Length -gt 65536) {
        throw 'The Splash Builder download manifest is missing or oversized.'
    }
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $required = @('tools/pack_splash.py', 'tools/splash_builder.py', 'tools/splash_project.py', 'LICENSE', 'LICENSES.md')
    $allowed = $required + @('tools/splash_motion.py')
    if ($manifest.format -ne 1 -or $manifest.pillow -notmatch '^\d+\.\d+\.\d+$' -or @($manifest.files).Count -notin @($required.Count, $allowed.Count)) {
        throw 'Unsupported Splash Builder download manifest.'
    }
    $seen = @{}
    foreach ($file in $manifest.files) {
        $name = [string]$file.path
        if ($name -cnotin $allowed -or $seen.ContainsKey($name) -or $file.sha256 -cnotmatch '^[a-f0-9]{64}$' -or $file.size -le 0 -or $file.size -gt 2MB) {
            throw 'Invalid Splash Builder file entry.'
        }
        $seen[$name] = $true
        $path = Join-Path $Folder $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -ne $file.size -or
            (Get-SplashHash $path) -cne $file.sha256) {
            throw "Splash Builder file failed verification: $name"
        }
    }
    foreach ($name in $required) {
        if (-not $seen.ContainsKey($name)) { throw "Missing Splash Builder file: $name" }
    }
    return $manifest
}

function Get-SplashDownload([string]$Url, [string]$Destination) {
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -UserAgent 'Gloam-Splash-Builder' -TimeoutSec 60
}

function Get-SplashCachedPackage([string]$Cache) {
    $pointer = Join-Path $Cache 'current.txt'
    if (-not (Test-Path -LiteralPath $pointer -PathType Leaf)) { throw 'No cached Splash Builder is available yet.' }
    $revision = ([IO.File]::ReadAllText($pointer)).Trim()
    if ($revision -cnotmatch '^[a-f0-9]{40}$') { throw 'Invalid cached builder revision.' }
    $folder = Join-Path $Cache ('versions/' + $revision)
    $null = Test-SplashPackage $folder
    return $folder
}

function Get-SplashPackage([string]$Cache, [string]$LocalSource, [bool]$UseOffline) {
    if ($LocalSource) {
        $folder = (Resolve-Path -LiteralPath $LocalSource).Path
        $null = Test-SplashPackage $folder
        return $folder
    }
    if ($UseOffline) { return Get-SplashCachedPackage $Cache }
    $staging = $null
    try {
        $repo = 'nextcode4u/gloam-shell-theme-directory'
        $commit = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/commits/main" -UserAgent 'Gloam-Splash-Builder' -TimeoutSec 30
        $revision = [string]$commit.sha
        if ($revision -cnotmatch '^[a-f0-9]{40}$') { throw 'Invalid builder revision.' }
        $folder = Join-Path $Cache ('versions/' + $revision)
        $valid = $false
        try { $null = Test-SplashPackage $folder; $valid = $true } catch { }
        if (-not $valid) {
            $staging = Join-Path $Cache ('download-' + [Guid]::NewGuid().ToString('N'))
            [IO.Directory]::CreateDirectory((Join-Path $staging 'tools')) | Out-Null
            $url = "https://raw.githubusercontent.com/$repo/$revision/"
            Get-SplashDownload ($url + 'tools/splash-downloads.json') (Join-Path $staging 'tools/splash-downloads.json')
            # Only fixed builder paths are downloaded; the manifest never supplies URLs or destinations.
            $files = @('tools/pack_splash.py','tools/splash_builder.py','tools/splash_project.py','LICENSE','LICENSES.md')
            $downloadManifest = Get-Content -Raw -LiteralPath (Join-Path $staging 'tools/splash-downloads.json') | ConvertFrom-Json
            if (@($downloadManifest.files.path) -ccontains 'tools/splash_motion.py') { $files += 'tools/splash_motion.py' }
            foreach ($name in $files) {
                Get-SplashDownload ($url + $name) (Join-Path $staging $name)
            }
            $null = Test-SplashPackage $staging
            [IO.Directory]::CreateDirectory((Join-Path $Cache 'versions')) | Out-Null
            if (Test-Path -LiteralPath $folder) {
                Move-Item -LiteralPath $folder -Destination ($folder + '.damaged-' + [Guid]::NewGuid().ToString('N'))
            }
            Move-Item -LiteralPath $staging -Destination $folder
            $staging = $null
        }
        $temporary = Join-Path $Cache ('current-' + [Guid]::NewGuid().ToString('N') + '.tmp')
        [IO.File]::WriteAllText($temporary, $revision)
        Move-Item -LiteralPath $temporary -Destination (Join-Path $Cache 'current.txt') -Force
        return $folder
    } catch {
        $failure = $_.Exception.Message
        try { $cached = Get-SplashCachedPackage $Cache } catch { throw "Could not get Splash Builder: $failure" }
        Write-Warning "Could not check for a newer builder. Using the verified cached copy. $failure"
        return $cached
    } finally {
        if ($staging -and (Test-Path -LiteralPath $staging)) { Remove-Item -LiteralPath $staging -Recurse -Force }
    }
}

function Test-SplashPython([string]$Executable) {
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable -PathType Leaf) -or $Executable -match '\\WindowsApps\\') { return $null }
    try {
        $probe = & $Executable -I -c "import sys,json,tkinter,venv; assert (3,10) <= sys.version_info[:2] <= (3,13); print(json.dumps(dict(path=sys.executable,version='%d.%d'%sys.version_info[:2])))" 2>$null
        if ($LASTEXITCODE -eq 0) { return ($probe | ConvertFrom-Json) }
    } catch { }
    return $null
}

function Find-SplashPython([string]$Requested) {
    if ($Requested) {
        $probe = Test-SplashPython $Requested
        if (-not $probe) { throw 'Choose a full Python 3.10-3.13 installation with Tk and venv.' }
        return $probe
    }
    $candidates = @()
    foreach ($name in @('python.exe','python3.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        # Listing installed interpreters does not ask the Python manager to install one.
        try {
            $listing = & $launcher.Source -0p 2>&1
            foreach ($line in $listing) {
                if ([string]$line -match '(?i)([a-z]:\\.+\\python(?:[0-9.]*)?\.exe)\s*$') { $candidates += $Matches[1] }
            }
        } catch { }
    }
    foreach ($base in @((Join-Path $env:LOCALAPPDATA 'Programs/Python'), (Join-Path $env:LOCALAPPDATA 'Python'))) {
        if (Test-Path -LiteralPath $base) {
            $candidates += @(Get-ChildItem -LiteralPath $base -Directory -ErrorAction SilentlyContinue | ForEach-Object { Join-Path $_.FullName 'python.exe' })
        }
    }
    foreach ($path in ($candidates | Select-Object -Unique)) {
        $probe = Test-SplashPython $path
        if ($probe) { return $probe }
    }
    return $null
}

function Install-SplashPython {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host 'WinGet is unavailable. Install Python with Tcl/Tk from python.org, then run this command again.'
        if ((Read-Host 'Open the official Python downloads page? [y/N]') -match '^(y|yes)$') {
            Start-Process 'https://www.python.org/downloads/windows/'
        }
        return $null
    }
    Write-Host 'Installing Python 3.13 for your Windows account through WinGet...'
    & $winget.Source install --id Python.Python.3.13 --exact --source winget --scope user --accept-source-agreements --accept-package-agreements | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Python installation did not finish. Choose an existing python.exe or try again.' }
    $probe = Find-SplashPython ''
    if (-not $probe) { throw 'Python was installed but could not be found with Tk. Reopen PowerShell and try again.' }
    return $probe
}

function Get-SplashEnvironment([object]$Interpreter, [string]$Cache, [string]$Pillow, [bool]$UseOffline) {
    $folder = Join-Path $Cache ('python/' + $Interpreter.version + '-pillow-' + $Pillow)
    $pythonExe = Join-Path $folder 'Scripts/python.exe'
    if (Test-SplashPython $pythonExe) {
        try {
            & $pythonExe -I -c "import PIL, PIL.ImageTk; assert PIL.__version__ == '$Pillow'" 2>$null
            if ($LASTEXITCODE -eq 0) { return $pythonExe }
        } catch { }
    }
    if ($UseOffline) { throw 'The private Python environment is not ready. Run once online to prepare it.' }
    Write-Host "Splash Builder needs Pillow $Pillow in its own Python environment. Existing Python packages will be left alone."
    if ((Read-Host 'Download and prepare these dependencies? [y/N]') -notmatch '^(y|yes)$') { throw 'Dependency setup cancelled.' }
    if (Test-Path -LiteralPath $folder) {
        Move-Item -LiteralPath $folder -Destination ($folder + '.previous-' + [Guid]::NewGuid().ToString('N'))
    }
    & $Interpreter.path -I -m venv $folder | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the private Python environment.' }
    & $pythonExe -I -m pip --isolated install --disable-pip-version-check --only-binary=:all: --index-url https://pypi.org/simple "Pillow==$Pillow" | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Pillow could not be installed. Check the connection and run the command again.' }
    & $pythonExe -I -c "import tkinter, PIL, PIL.ImageTk; assert PIL.__version__ == '$Pillow'"
    if ($LASTEXITCODE -ne 0) { throw 'The new Python environment could not be verified.' }
    return $pythonExe
}

function Start-SplashBuilder {
    param([string]$WorkingFolder, [string]$PythonPath, [string]$Cache, [string]$LocalSource, [bool]$UseOffline, [bool]$PrepareOnly)
    $ErrorActionPreference = 'Stop'
    Set-StrictMode -Version Latest
    if ($env:OS -ne 'Windows_NT') { throw 'Use this launch command in Windows PowerShell. Other systems can run tools/pack_splash.py.' }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    if (-not $Cache) { $Cache = Join-Path $env:LOCALAPPDATA 'Gloam/SplashBuilder' }
    [IO.Directory]::CreateDirectory($Cache) | Out-Null
    $folder = Get-SplashPackage $Cache $LocalSource $UseOffline
    $manifest = Test-SplashPackage $folder
    $interpreter = Find-SplashPython $PythonPath
    while (-not $interpreter) {
        if ($UseOffline) { throw 'Python with Tk is missing. Run once online to set it up.' }
        Write-Host 'Splash Builder needs Python 3.10-3.13 with Tcl/Tk.'
        Write-Host '1. Install Python 3.13 for this Windows account (WinGet)'
        Write-Host '2. Use an existing python.exe'
        Write-Host '3. Cancel'
        switch (Read-Host 'Choose 1, 2 or 3') {
            '1' { $interpreter = Install-SplashPython; if (-not $interpreter) { return } }
            '2' { $interpreter = Find-SplashPython ((Read-Host 'Full path to python.exe').Trim('"')) }
            default { return }
        }
    }
    $pythonExe = Get-SplashEnvironment $interpreter $Cache $manifest.pillow $UseOffline
    Write-Host 'Splash Builder is ready. Select a working folder to create or resume a project.'
    if (-not $PrepareOnly) {
        $arguments = @((Join-Path $folder 'tools/splash_builder.py'))
        if ($WorkingFolder) { $arguments += @('--workspace', $WorkingFolder) }
        & $pythonExe @arguments
        if ($LASTEXITCODE -ne 0) { throw 'Splash Builder stopped with an error. Your saved project remains in its working folder.' }
    }
}

if (-not $LibraryOnly) {
    Start-SplashBuilder -WorkingFolder $Workspace -PythonPath $Python -Cache $CacheDirectory -LocalSource $SourceDirectory -UseOffline $Offline.IsPresent -PrepareOnly $NoLaunch.IsPresent
}
