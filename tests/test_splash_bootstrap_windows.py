# SPDX-License-Identifier: GPL-3.0-or-later
"""Native PowerShell checks with local fixtures; never run a Python installer."""

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
class BootstrapTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(
            prefix="splash bootstrap ", dir=ROOT / "build"
        )
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.package = self.folder / "package"
        self.cache = self.folder / "cache"
        self.cache.mkdir()
        manifest = json.loads((ROOT / "tools/splash-downloads.json").read_text())
        for name in [entry["path"] for entry in manifest["files"]] + [
            "tools/splash-downloads.json"
        ]:
            target = self.package / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.preamble = (
            "$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest; . "
            + literal(win(ROOT / "splash.ps1"))
            + " -LibraryOnly; "
        )
        self.preamble += (
            "$package="
            + literal(win(self.package))
            + "; $cache="
            + literal(win(self.cache))
            + "; "
        )

    def run_ps(self, code):
        encoded = base64.b64encode((self.preamble + code).encode("utf-16le")).decode()
        result = subprocess.run(
            [
                PS,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-EncodedCommand",
                encoded,
            ],
            capture_output=True,
            timeout=45,
        )
        output = result.stdout.decode(errors="replace") + result.stderr.decode(
            errors="replace"
        )
        self.assertEqual(result.returncode, 0, output)
        return output

    def test_manifest_validation_and_tampering(self):
        self.run_ps("$null=Test-SplashPackage $package; Write-Output 'Verified'")
        (self.package / "tools/splash_project.py").write_bytes(b"changed")
        self.run_ps(
            "$failed=$false; try { $null=Test-SplashPackage $package } catch { $failed=$true }; if(-not $failed){throw 'Tampering accepted'}"
        )

    def test_unknown_manifest_destinations_rejected(self):
        path = self.package / "tools/splash-downloads.json"
        data = json.loads(path.read_text())
        data["files"][0]["path"] = "../outside.py"
        path.write_text(json.dumps(data))
        self.run_ps(
            "$failed=$false; try { $null=Test-SplashPackage $package } catch { $failed=$true }; if(-not $failed){throw 'Escaping path accepted'}"
        )

    def test_failed_update_keeps_verified_cached_snapshot(self):
        revision = "a" * 40
        cached = self.cache / "versions" / revision
        shutil.copytree(self.package, cached)
        (self.cache / "current.txt").write_text(revision)
        self.run_ps(r"""
function Invoke-RestMethod { return [pscustomobject]@{ sha=('b'*40) } }
function Get-SplashDownload([string]$Url,[string]$Destination) {
    if($Url.EndsWith('tools/splash-downloads.json')) { Copy-Item -LiteralPath (Join-Path $package 'tools/splash-downloads.json') -Destination $Destination }
    else { [IO.File]::WriteAllText($Destination,'incomplete download') }
}
$actual=Get-SplashPackage $cache '' $false
if($actual -ne (Join-Path $cache ('versions/'+('a'*40)))) { throw 'Did not preserve cached version' }
if(([IO.File]::ReadAllText((Join-Path $cache 'current.txt'))).Trim() -ne ('a'*40)) { throw 'Published partial update' }
if(@(Get-ChildItem -LiteralPath $cache -Filter 'download-*').Count) { throw 'Staging download leaked' }
$null=Get-SplashPackage $cache '' $true
""")

    def test_cancelled_python_setup_does_not_install(self):
        self.run_ps(r"""
function Find-SplashPython { return $null }
function Read-Host { return '3' }
function Install-SplashPython { throw 'Installer must not run after cancellation' }
function Get-SplashEnvironment { throw 'Dependencies must not install after cancellation' }
Start-SplashBuilder -LocalSource $package -Cache $cache -PrepareOnly $true
""")

    def test_declined_dependencies_and_offline_mode_do_not_install(self):
        self.run_ps(r"""
function Read-Host { return 'n' }
$probe=[pscustomobject]@{path='must-not-execute.exe';version='3.13'}
foreach($offline in @($false,$true)) {
    $failed=$false
    try { $null=Get-SplashEnvironment $probe $cache '11.3.0' $offline } catch { $failed=$true }
    if(-not $failed){ throw 'Missing environment accepted' }
}
if(Test-Path -LiteralPath (Join-Path $cache 'python')) { throw 'Dependencies written despite refusal' }
""")

    def test_detects_existing_python_with_tk(self):
        self.run_ps(r"""
$probe=Find-SplashPython ''
if(-not $probe -or $probe.version -notmatch '^3\.(10|11|12|13)$') { throw 'No compatible interpreter detected' }
if(-not (Test-Path -LiteralPath $probe.path -PathType Leaf)) { throw 'Interpreter path invalid' }
""")


if __name__ == "__main__":
    unittest.main()
