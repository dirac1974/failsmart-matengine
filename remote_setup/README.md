# Remote Compute Setup on a Friend's Windows PC

Turns a friend's Windows PC (for example one with an RTX 5090) into a machine you can run jobs on from your laptop, with one phone call and no technical work on his side.

**What you end up with:** `ssh dftguest@friend-gpu` from your laptop, landing in a standard Windows account with its own Ubuntu (WSL2) that can use his GPU. Access goes over Tailscale only; nothing is opened on his router.

**Status:** the shell scripts were syntax-checked and the keep-alive checker was run. The PowerShell scripts have **not** been run on a Windows machine. Watch the output the first time.

| File | Run where | By whom |
|---|---|---|
| `setup-friend-pc.ps1` | His PC, administrator PowerShell, during the call | You, through Quick Assist |
| `setup-guest-wsl.ps1` | His PC, over SSH, as the guest account | You |
| `setup-wsl.sh` | Inside Ubuntu on his PC | You |
| `keepalive-test.sh` | Inside Ubuntu on his PC | You |

---

## Before the call (10 minutes, on your laptop)

1. **Make an SSH key** if you have none: `ssh-keygen -t ed25519`. Copy the single line in `~/.ssh/id_ed25519.pub`.
2. **Create a Tailscale account** at https://tailscale.com and install Tailscale on your laptop.
3. **Generate a one-time auth key:** Tailscale admin console, Settings, Keys, "Generate auth key" (one-off, expires in a day). Copy it. With it, his PC joins your network with no browser login.
4. **Sign in to Quick Assist** on your laptop (Start menu, "Quick Assist") with a Microsoft account.
5. **Ask him to be at the PC for about 30 to 45 minutes** and to know his Windows password.

## During the call

1. **Connect.** You: Quick Assist, "Help someone", read him the code. Him: press `Win + Ctrl + Q`, type the code, click Allow. Then request full control; he clicks Allow again.
2. **Check virtualization.** Task Manager, Performance, CPU: "Virtualization: Enabled". If it says Disabled, he must turn it on in the BIOS (usually "SVM Mode" on AMD or "Intel VT-x"); talk him through it by phone, since no remote tool works there.
3. **Open administrator PowerShell.** Right-click Start, "Terminal (Admin)". He clicks Yes on the prompt (your view pauses while it is on screen).
4. **Download and run the script** (one paste; replace the two quoted values):

   ```powershell
   cd $env:TEMP
   iwr https://raw.githubusercontent.com/dirac1974/failsmart-matengine/remote-setup/remote_setup/setup-friend-pc.ps1 -OutFile setup-friend-pc.ps1
   powershell -ExecutionPolicy Bypass -File .\setup-friend-pc.ps1 -PublicKey "ssh-ed25519 AAAA...your key..." -TailscaleAuthKey "tskey-auth-..."
   ```

   Read the script first if you like: it is plain text and prints each step.
5. **Write down** the account name and password it prints at the end.
6. **Test from your laptop while he is still on the call:** `ssh dftguest@friend-gpu`. You should get a Windows prompt without a password.
7. **Show him the off switch** (see the note below), then restart the PC: `shutdown /r /t 0`. The Quick Assist session ends; that is expected. He can hang up.

## After the restart (you, alone)

```powershell
ssh dftguest@friend-gpu
iwr https://raw.githubusercontent.com/dirac1974/failsmart-matengine/remote-setup/remote_setup/setup-guest-wsl.ps1 -OutFile setup-guest-wsl.ps1
powershell -ExecutionPolicy Bypass -File .\setup-guest-wsl.ps1
wsl -d Ubuntu-24.04
```

The first start of Ubuntu asks for a Linux username and password. Then, inside Ubuntu:

```bash
curl -fsSLO https://raw.githubusercontent.com/dirac1974/failsmart-matengine/remote-setup/remote_setup/setup-wsl.sh
curl -fsSLO https://raw.githubusercontent.com/dirac1974/failsmart-matengine/remote-setup/remote_setup/keepalive-test.sh
bash setup-wsl.sh --gpu-ml
bash keepalive-test.sh start
```

Log out completely, wait five minutes, log back in and run `bash keepalive-test.sh check`. Do not start a long run until it prints `PASS`.

## Day-to-day use

- **Connect:** `ssh dftguest@friend-gpu`, then `wsl`.
- **Run jobs in tmux** so they survive a disconnect: `tmux new -s run`, start the job, detach with `Ctrl-b` then `d`, return with `tmux attach -t run`.
- **Check the GPU is free first:** `nvidia-smi`. Agree hours with him (overnight, for example); a run on his GPU will slow his games.
- **Copy files:** `scp -r runs/ dftguest@friend-gpu:` from your laptop, and back the same way. Inside WSL your Windows home is `/mnt/c/Users/dftguest`.

## If something goes wrong

| Symptom | Likely cause and fix |
|---|---|
| Script says virtualization is disabled | BIOS setting; see step 2 of the call |
| `ssh` asks for a password | The key was not installed. Log in with the printed password, then follow the one-line command the script printed |
| `ssh` cannot find `friend-gpu` | Tailscale is not connected on one side. On his PC: `tailscale status`. Use the `100.x.y.z` address the script printed instead of the name |
| `wsl` fails over SSH on first start | Some Windows builds need an interactive session for the first launch. Do a short second Quick Assist session with him signed in as the guest account, start Ubuntu once, then SSH works |
| `keepalive-test.sh check` fails | The Linux VM was stopped while you were away. Confirm `vmIdleTimeout=-1` in `C:\Users\dftguest\.wslconfig`, run `wsl --shutdown`, retry. If it still fails, keep one SSH session open with `wsl` running during long jobs |
| `nvidia-smi` missing inside Ubuntu | Update the NVIDIA driver on Windows. Never install a Linux GPU driver inside WSL |

## Note to give your friend

> I set up a separate, non-administrator account on your PC called `dftguest` so I can run calculations on your graphics card when you are not using it. It cannot see your files or change your settings.
>
> - **To pause my access:** right-click the Tailscale icon near the clock and choose Exit.
> - **To remove everything:** open PowerShell as administrator and run `C:\Users\<you>\AppData\Local\Temp\setup-friend-pc.ps1 -Undo`, or just tell me and I will do it.
> - **What changed on your PC:** the new account, Tailscale, Windows' built-in remote login (reachable only through Tailscale), the Windows Linux feature, and the PC no longer sleeps while plugged in.
> - If the PC feels slow or the fans are loud, I am probably running something. Message me and I will stop it.

## What the first script changes, exactly

| Change | Reversed by `-Undo` |
|---|---|
| Creates standard local account `dftguest` with a random password | Yes (the files in `C:\Users\dftguest` stay until deleted) |
| Installs and starts OpenSSH Server; firewall allows port 22 only from `100.64.0.0/10` (Tailscale) | Service stopped and disabled |
| Writes your public key to `C:\Users\dftguest\.ssh\authorized_keys` | Removed with the account folder |
| Sets sleep and hibernate on AC power to Never | Restored to the recorded value |
| Installs Tailscale, sets it to stay connected when logged out, joins your network | Logged out (uninstall from Settings, Apps) |
| Enables the WSL2 Windows feature | No (remove from "Turn Windows features on or off") |

Sources: Tailscale MSI and policy settings (https://tailscale.com/docs/install/windows/msi), WSL commands (https://learn.microsoft.com/en-us/windows/wsl/basic-commands).
