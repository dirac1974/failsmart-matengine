<#
.SYNOPSIS
  One-paste setup of a friend's Windows PC as a remote compute box (run in an
  elevated PowerShell during a Quick Assist session).

.DESCRIPTION
  Does, in order:
    0. Pre-flight checks (admin, virtualization, GPU) and prints what it will change
    1. Creates a standard (non-admin) Windows account for the guest
    2. Enables the built-in OpenSSH Server, limited to the Tailscale network
    3. Installs the guest's SSH public key
    4. Stops the PC sleeping while plugged in
    5. Installs Tailscale and connects it (unattended mode)
    6. Enables WSL2 (no Linux distribution yet; that is installed later as the guest)
  A restart is needed at the end. After it, the guest connects with SSH and
  finishes inside Linux with setup-wsl.sh.

  Run again with -Undo to reverse everything this script changed.

  NOT TESTED on the target machine. Read the output as it runs.

.PARAMETER GuestUser
  Name of the Windows account to create. Default: dftguest

.PARAMETER PublicKey
  The guest's SSH public key (one line starting with ssh-ed25519 or ssh-rsa).
  Create one on the guest's laptop with:  ssh-keygen -t ed25519

.PARAMETER TailscaleAuthKey
  Optional one-time auth key from the guest's Tailscale admin console
  (Settings > Keys > Generate auth key). Without it a browser login opens.

.PARAMETER TailscaleHostName
  Name the PC will have on the Tailscale network. Default: friend-gpu

.PARAMETER Undo
  Remove the guest account, close SSH, restore sleep settings, log Tailscale out.

.EXAMPLE
  .\setup-friend-pc.ps1 -PublicKey "ssh-ed25519 AAAA... david@laptop" -TailscaleAuthKey "tskey-auth-..."
#>
[CmdletBinding()]
param(
    [string]$GuestUser = "dftguest",
    [string]$PublicKey = "",
    [string]$TailscaleAuthKey = "",
    [string]$TailscaleHostName = "friend-gpu",
    [switch]$SkipTailscale,
    [switch]$SkipWsl,
    [switch]$Undo
)

$ErrorActionPreference = "Stop"
$StateFile = Join-Path $env:ProgramData "remote-compute-setup.json"
$TailscaleExe = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
$TailscaleNet = "100.64.0.0/10"   # Tailscale address range; SSH is limited to it
$SshRule = "OpenSSH-Server-In-TCP"

function Say($msg)  { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    WARNING: $msg" -ForegroundColor Yellow }

# Windows PowerShell 5.1 turns redirected stderr from native programs into errors when
# ErrorActionPreference is Stop. Run such programs through this helper.
function Invoke-Native([scriptblock]$Block) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Block } finally { $ErrorActionPreference = $old }
}

function Assert-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this in PowerShell started with 'Run as administrator'."
    }
}

function New-RandomPassword {
    $chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    $bytes = New-Object byte[] 20
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $pw = -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
    return $pw + "!7a"   # satisfy complexity rules
}

# ---------------------------------------------------------------------------
# Undo
# ---------------------------------------------------------------------------
if ($Undo) {
    Assert-Admin
    $state = if (Test-Path $StateFile) { Get-Content $StateFile -Raw | ConvertFrom-Json } else { $null }
    $user = if ($state) { $state.GuestUser } else { $GuestUser }

    Say "Removing guest account '$user'"
    if (Get-LocalUser -Name $user -ErrorAction SilentlyContinue) {
        Remove-LocalUser -Name $user
        Ok "account removed (its files stay in C:\Users\$user until you delete that folder)"
    } else { Ok "account not present" }

    Say "Closing SSH"
    if (Get-Service sshd -ErrorAction SilentlyContinue) {
        Stop-Service sshd -Force -ErrorAction SilentlyContinue
        Set-Service sshd -StartupType Disabled
        Ok "OpenSSH Server stopped and disabled"
    }

    Say "Restoring sleep settings"
    if ($state -and $state.SleepAcMinutes -ne $null) {
        powercfg /change standby-timeout-ac $state.SleepAcMinutes | Out-Null
        Ok "sleep on AC power set back to $($state.SleepAcMinutes) minutes"
    } else {
        powercfg /change standby-timeout-ac 30 | Out-Null
        Ok "sleep on AC power set to 30 minutes (previous value was not recorded)"
    }

    Say "Logging Tailscale out"
    if (Test-Path $TailscaleExe) {
        Invoke-Native { & $TailscaleExe logout 2>$null | Out-Null }
        Ok "logged out. Uninstall Tailscale from Settings > Apps if you no longer want it."
    }
    Remove-Item $StateFile -ErrorAction SilentlyContinue
    Write-Host "`nDone. WSL was left enabled; remove it from 'Turn Windows features on or off' if unwanted." -ForegroundColor Green
    return
}

# ---------------------------------------------------------------------------
# 0. Pre-flight
# ---------------------------------------------------------------------------
Assert-Admin
Say "Pre-flight checks"

$os = Get-CimInstance Win32_OperatingSystem
Ok "$($os.Caption) build $($os.BuildNumber)"
if ([int]$os.BuildNumber -lt 19041) { throw "Windows build 19041 or newer is required for WSL2." }

$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$hypervisorUp = (Get-CimInstance Win32_ComputerSystem).HypervisorPresent
if ($hypervisorUp -or $cpu.VirtualizationFirmwareEnabled) {
    Ok "virtualization is enabled"
} else {
    Warn "virtualization looks DISABLED in the BIOS. WSL2 will not start until it is turned on"
    Warn "(BIOS setting usually called 'SVM Mode' on AMD or 'Intel VT-x'). Continuing with the other steps."
}
Ok "CPU: $($cpu.Name.Trim()), $($cpu.NumberOfCores) cores; RAM: $([math]::Round($os.TotalVisibleMemorySize / 1MB)) GB"

$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($smi) {
    $gpu = (& nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader) -join "; "
    Ok "GPU: $gpu"
} else {
    Warn "nvidia-smi not found. Install or update the NVIDIA driver before GPU runs."
}

if (-not $PublicKey) {
    Warn "no -PublicKey given: the guest will log in with the password printed below."
} elseif ($PublicKey -notmatch '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp\d+) [A-Za-z0-9+/=]+') {
    throw "-PublicKey does not look like an SSH public key (it should start with ssh-ed25519 or ssh-rsa)."
}

$state = [ordered]@{ GuestUser = $GuestUser; Date = (Get-Date).ToString("s") }

# ---------------------------------------------------------------------------
# 1. Guest account (standard user)
# ---------------------------------------------------------------------------
Say "Creating standard account '$GuestUser'"
$plain = $null
if (Get-LocalUser -Name $GuestUser -ErrorAction SilentlyContinue) {
    Ok "account already exists; leaving its password unchanged"
} else {
    $plain = New-RandomPassword
    $secure = ConvertTo-SecureString $plain -AsPlainText -Force
    New-LocalUser -Name $GuestUser -Password $secure -PasswordNeverExpires `
        -Description "Remote compute guest (remove with setup-friend-pc.ps1 -Undo)" | Out-Null
    Add-LocalGroupMember -Group "Users" -Member $GuestUser
    Ok "created as a standard user (not an administrator)"
}

# ---------------------------------------------------------------------------
# 2. OpenSSH Server, reachable only from the Tailscale network
# ---------------------------------------------------------------------------
Say "Enabling OpenSSH Server"
$cap = Get-WindowsCapability -Online -Name "OpenSSH.Server*" | Select-Object -First 1
if ($cap.State -ne "Installed") {
    Add-WindowsCapability -Online -Name $cap.Name | Out-Null
    Ok "installed $($cap.Name)"
} else { Ok "already installed" }
Set-Service sshd -StartupType Automatic
Start-Service sshd

if (-not (Get-NetFirewallRule -Name $SshRule -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name $SshRule -DisplayName "OpenSSH Server (Tailscale only)" -Enabled True `
        -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -RemoteAddress $TailscaleNet | Out-Null
} else {
    Set-NetFirewallRule -Name $SshRule -Enabled True -RemoteAddress $TailscaleNet
}
Ok "sshd running; firewall allows port 22 only from $TailscaleNet"

# ---------------------------------------------------------------------------
# 3. SSH public key for the guest
# ---------------------------------------------------------------------------
if ($PublicKey) {
    Say "Installing the guest's SSH key"
    $profileDir = Join-Path $env:SystemDrive "Users\$GuestUser"
    if (-not (Test-Path $profileDir) -and $plain) {
        # Create the profile folder by starting a process as the new user
        try {
            $cred = New-Object Management.Automation.PSCredential(".\$GuestUser", (ConvertTo-SecureString $plain -AsPlainText -Force))
            Start-Process cmd.exe -ArgumentList "/c exit" -Credential $cred -LoadUserProfile -WindowStyle Hidden -Wait
        } catch { Warn "could not pre-create the profile: $($_.Exception.Message)" }
    }
    if (Test-Path $profileDir) {
        $sshDir = Join-Path $profileDir ".ssh"
        $keyFile = Join-Path $sshDir "authorized_keys"
        New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
        Set-Content -Path $keyFile -Value $PublicKey -Encoding ascii
        # sshd refuses key files that other users can write
        icacls $sshDir /inheritance:r /grant "${GuestUser}:(OI)(CI)F" /grant "SYSTEM:(OI)(CI)F" /grant "Administrators:(OI)(CI)F" | Out-Null
        Ok "key written to $keyFile"
    } else {
        Warn "profile folder not created yet. After the first password login, the guest runs on their laptop:"
        Warn "  type `$env:USERPROFILE\.ssh\id_ed25519.pub | ssh $GuestUser@$TailscaleHostName `"mkdir .ssh 2>nul & more >> .ssh\authorized_keys`""
    }
}

# ---------------------------------------------------------------------------
# 4. Keep the PC awake on AC power
# ---------------------------------------------------------------------------
Say "Stopping sleep while plugged in"
try {
    $q = powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE
    $hex = ($q | Select-String "Current AC Power Setting Index").ToString().Split(":")[-1].Trim()
    $state.SleepAcMinutes = [int]([Convert]::ToInt32($hex, 16) / 60)
} catch { $state.SleepAcMinutes = $null }
powercfg /change standby-timeout-ac 0 | Out-Null
powercfg /change hibernate-timeout-ac 0 | Out-Null
Ok "sleep and hibernate on AC power set to Never (was $($state.SleepAcMinutes) minutes); the screen can still turn off"

# ---------------------------------------------------------------------------
# 5. Tailscale
# ---------------------------------------------------------------------------
if (-not $SkipTailscale) {
    Say "Installing Tailscale"
    if (-not (Test-Path $TailscaleExe)) {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            Invoke-Native { winget install --id Tailscale.Tailscale -e --silent --accept-package-agreements --accept-source-agreements }
        }
        if (-not (Test-Path $TailscaleExe)) {
            Warn "automatic install did not work. Download and run the installer from https://tailscale.com/download/windows"
            Warn "then run this script again (finished steps are skipped)."
        }
    } else { Ok "already installed" }

    if (Test-Path $TailscaleExe) {
        # Stay connected when nobody is logged in to Windows
        New-Item -Path "HKLM:\SOFTWARE\Policies\Tailscale" -Force | Out-Null
        Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Tailscale" -Name "UnattendedMode" -Value "always" -Type String
        $upArgs = @("up", "--unattended", "--hostname=$TailscaleHostName")
        if ($TailscaleAuthKey) { $upArgs += "--auth-key=$TailscaleAuthKey" }
        else { Warn "no auth key given: a browser window will open. Log in with the GUEST's Tailscale account." }
        Invoke-Native { & $TailscaleExe @upArgs }
        Start-Sleep -Seconds 3
        $ip = Invoke-Native { & $TailscaleExe ip -4 2>$null | Select-Object -First 1 }
        if ($ip) { Ok "connected as '$TailscaleHostName' with address $ip"; $state.TailscaleIp = $ip }
        else { Warn "Tailscale is installed but not connected yet. Finish the login, then run: tailscale ip -4" }
    }
}

# ---------------------------------------------------------------------------
# 6. WSL2 platform (the Linux distribution is installed later, as the guest)
# ---------------------------------------------------------------------------
$needRestart = $false
if (-not $SkipWsl) {
    Say "Enabling WSL2"
    $wslOk = $false
    try { Invoke-Native { wsl --status *> $null }; $wslOk = ($LASTEXITCODE -eq 0) } catch { $wslOk = $false }
    if ($wslOk) {
        Ok "WSL is already installed"
        Invoke-Native { wsl --update 2>$null | Out-Null }
    } else {
        Invoke-Native { wsl --install --no-distribution }
        $needRestart = $true
        Ok "WSL components installed; a restart is required"
    }
}

$state | ConvertTo-Json | Set-Content -Path $StateFile -Encoding utf8

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host "`n================= WRITE THIS DOWN =================" -ForegroundColor Magenta
Write-Host " Windows account : $GuestUser"
if ($plain) { Write-Host " Password        : $plain   (shown once)" }
Write-Host " Tailscale name  : $TailscaleHostName   address: $($state.TailscaleIp)"
Write-Host " Connect with    : ssh $GuestUser@$TailscaleHostName"
Write-Host "===================================================" -ForegroundColor Magenta
Write-Host "`nTest the SSH login from the guest's laptop NOW, before restarting."
if ($needRestart) { Write-Host "Then restart this PC to finish the WSL install:  shutdown /r /t 0" -ForegroundColor Yellow }
Write-Host "To reverse everything later:  .\setup-friend-pc.ps1 -Undo"
