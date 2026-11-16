# SPDX-License-Identifier: GPL-3.0-or-later
"""Verify Theme Studio's Windows launcher without downloading or installing tools."""

import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PS = (
    shutil.which("powershell.exe")
    or "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
)


def win(path):
    return (
        str(path)
        if os.name == "nt"
        else subprocess.check_output(["wslpath", "-w", str(path)], text=True).strip()
    )


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(Path(PS).is_file(), "Needs Windows PowerShell")
class ThemeBootstrapTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(
            prefix="theme bootstrap ", dir=ROOT / "build"
        )
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.package = self.folder / "package"
        self.cache = self.folder / "cache"
        self.cache.mkdir()
        manifest = json.loads((ROOT / "tools/theme-downloads.json").read_text())
        for name in [item["path"] for item in manifest["files"]] + [
            "tools/theme-downloads.json"
        ]:
            target = self.package / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.preamble = (
            "$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest; . "
            + literal(win(ROOT / "theme.ps1"))
            + " -LibraryOnly; $package="
            + literal(win(self.package))
            + "; $cache="
            + literal(win(self.cache))
            + "; "
        )

    def ps(self, code):
        command = base64.b64encode((self.preamble + code).encode("utf-16le")).decode()
        result = subprocess.run(
            [
                PS,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                command,
            ],
            capture_output=True,
            timeout=45,
        )
        self.assertEqual(
            result.returncode,
            0,
            result.stdout.decode(errors="replace")
            + result.stderr.decode(errors="replace"),
        )

    def test_complete_package_and_changed_browser_code_verification(self):
        self.ps("$null=Test-ThemePackage $package")
        (self.package / "tools/theme_studio/studio.js").write_text("changed")
        self.ps(
            "$failed=$false;try{$null=Test-ThemePackage $package}catch{$failed=$true};if(-not $failed){throw 'Modified code accepted'}"
        )

    def test_manifest_cannot_supply_paths_or_destinations(self):
        file = self.package / "tools/theme-downloads.json"
        data = json.loads(file.read_text())
        data["files"][0]["path"] = "../outside.py"
        file.write_text(json.dumps(data))
        self.ps(
            "$failed=$false;try{$null=Test-ThemePackage $package}catch{$failed=$true};if(-not $failed){throw 'Escaping path accepted'}"
        )

    def test_failed_refresh_retains_verified_cached_revision(self):
        revision = "a" * 40
        shutil.copytree(self.package, self.cache / "versions" / revision)
        (self.cache / "current.txt").write_text(revision)
        self.ps(r"""
function Invoke-RestMethod { return [pscustomobject]@{sha=('b'*40)} }
function Get-ThemeDownload([string]$Url,[string]$Destination) {
 if($Url.EndsWith('tools/theme-downloads.json')){Copy-Item -LiteralPath (Join-Path $package 'tools/theme-downloads.json') -Destination $Destination}
 else{[IO.File]::WriteAllText($Destination,'incomplete')}
}
$actual=Get-ThemePackage $cache '' $false
if($actual -ne (Join-Path $cache ('versions/'+('a'*40)))){throw 'Verified fallback lost'}
if(@(Get-ChildItem -LiteralPath $cache -Filter 'download-*').Count){throw 'Staging leaked'}
$null=Get-ThemePackage $cache '' $true
""")

    def test_cancelled_or_offline_dependency_setup_never_installs(self):
        self.ps(r"""
function Find-ThemePython { return $null }
function Read-Host { return '3' }
function Install-ThemePython { throw 'Must not install' }
Start-ThemeStudio -LocalSource $package -Cache $cache -PrepareOnly $true
function Read-Host { return 'n' }
$probe=[pscustomobject]@{path='must-not-execute.exe';version='3.13'}
foreach($offline in @($false,$true)){
 $failed=$false;try{$null=Get-ThemeEnvironment $probe $cache '11.3.0' $offline}catch{$failed=$true}
 if(-not $failed){throw 'Missing environment accepted'}
}
if(Test-Path -LiteralPath (Join-Path $cache 'python')){throw 'Dependency setup occurred after refusal'}
""")


if __name__ == "__main__":
    unittest.main()
