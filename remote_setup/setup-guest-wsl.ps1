<#
.SYNOPSIS
  Step 2, run by the GUEST over SSH after the restart (no administrator rights needed).
  Installs Ubuntu for the guest account and writes a .wslconfig sized to the machine.

.EXAMPLE
  ssh dftguest@friend-gpu
  powershell -ExecutionPolicy Bypass -File setup-guest-wsl.ps1

  NOT TESTED on the target machine.
#>
[CmdletBinding()]
param(
    [string]$Distro = "Ubuntu-24.04",
    # Share of the PC's memory Linux may use. The owner keeps the rest.
    [double]$MemoryFraction = 0.6
)
$ErrorActionPreference = "Stop"

$ramGb = [math]::Floor((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB)
$memGb = [math]::Max(8, [math]::Floor($ramGb * $MemoryFraction))
$cores = (Get-CimInstance Win32_Processor | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum

$cfg = @"
[wsl2]
memory=${memGb}GB
processors=$cores
# Keep the Linux VM alive when no terminal is attached, so detached jobs survive.
# Check this with keepalive-test.sh before any long run.
vmIdleTimeout=-1
"@
$cfgPath = Join-Path $env:USERPROFILE ".wslconfig"
Set-Content -Path $cfgPath -Value $cfg -Encoding ascii
Write-Host "Wrote $cfgPath (memory ${memGb} of ${ramGb} GB, $cores logical processors)"

# Native programs that write to stderr must not abort the script (Windows PowerShell 5.1)
$ErrorActionPreference = "Continue"
$have = (wsl --list --quiet 2>$null) -replace "`0", ""
if ($have -match [regex]::Escape($Distro)) {
    Write-Host "$Distro is already installed for this account."
} else {
    Write-Host "Installing $Distro for this account (a few minutes)..."
    wsl --install --distribution $Distro --no-launch
}
wsl --shutdown

Write-Host ""
Write-Host "Next:"
Write-Host "  1. Start Linux:            wsl -d $Distro"
Write-Host "     The first start asks you to choose a Linux username and password."
Write-Host "     If it fails over SSH, do this one step in a Quick Assist session"
Write-Host "     while signed in to Windows as this account."
Write-Host "  2. Inside Linux, run:      bash setup-wsl.sh"
