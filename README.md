# msikvm

A small cross-platform CLI that switches the input source of an MSI monitor over USB, for example from USB-C to DisplayPort. It does the same thing as MSI's Windows-only Gaming Intelligence / OSD app, without the app.

```sh
./msikvm.py set dp      # switch to DisplayPort
./msikvm.py set usbc    # switch to USB-C
./msikvm.py toggle      # flip between USB-C and DisplayPort
```

## Supported monitors

Built for and tested with the **MSI MPG 321UX OLED**.

Other MSI monitors with the same USB control device, which shows up as **"MSI Gaming Controller"** with USB ID `1462:3fa4`, probably work too. Many MAG and MPG models have it. Their input numbering can differ, though. Check what `get` reports before you rely on `set`.

To see whether your monitor has the device:

- **macOS:** `system_profiler SPUSBDataType | grep -A8 "MSI Gaming Controller"`
- **Linux:** `lsusb -d 1462:3fa4`
- **Windows:** Device Manager → Human Interface Devices, look for VID `1462` / PID `3FA4`

## Requirements

- The monitor's **USB upstream cable** (USB-B, or USB-C with data) must be connected to the computer that runs the command. Commands travel over USB, not over the video cable.
- Python 3.9 or newer.

## Installation

### Option 1: with uv (recommended)

[uv](https://docs.astral.sh/uv/) reads the dependency declared inside the script and installs it automatically on first run.

```sh
git clone https://github.com/dkvdm/msikvm.git
cd msikvm
chmod +x msikvm.py
./msikvm.py get
```

To make it available everywhere, symlink it onto your `PATH`:

```sh
ln -s "$PWD/msikvm.py" ~/.local/bin/msikvm
```

### Option 2: with pip

```sh
git clone https://github.com/dkvdm/msikvm.git
cd msikvm
python3 -m pip install hidapi
python3 msikvm.py get
```

The `hidapi` package includes prebuilt binaries for macOS, Linux, and Windows, so you don't need to install a separate system library.

### Linux: allow non-root access

By default only root can open the HID device. Add a udev rule:

```sh
sudo tee /etc/udev/rules.d/51-msi-gaming-device.rules >/dev/null <<'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="1462", ATTR{idProduct}=="3fa4", TAG+="uaccess"
KERNEL=="hidraw*", ATTRS{idVendor}=="1462", ATTRS{idProduct}=="3fa4", TAG+="uaccess"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

Then unplug the monitor's USB cable and plug it back in.

### Windows

The script runs on Windows without extra drivers. Use `python` instead of `./`:

```powershell
uv run msikvm.py get       # with uv
python msikvm.py get       # with pip
```

The `chmod` and symlink steps above don't apply.

#### One-click switch to USB-C

[`windows/usbc.exe`](windows/usbc.exe) is a standalone executable that runs `msikvm.py set usbc`. It doesn't need Python, and it doesn't open a console window. If something goes wrong, it shows an error dialog. Pin it to the taskbar, or create a shortcut to it and assign a key under the shortcut's Properties → Shortcut key.

To rebuild it after changing the script, run [`windows\build.bat`](windows/build.bat). On first run it creates a virtual environment in `windows\.venv` with `hidapi` and `pyinstaller`, so you need Python 3.9 or newer.

## Usage

```
msikvm.py [-m N] <command>

  list              List attached MSI monitors
  get               Print the current input (hdmi1, hdmi2, dp, usbc)
  set <input>       Switch to an input
  toggle [a] [b]    Switch to b if the current input is a, otherwise to a (default: usbc dp)
  raw <code>        Read a raw setting code, e.g. 00500 (read-only)

  -m, --monitor N   Choose which monitor to control (index from `list`, default 0)
```

Accepted input names: `hdmi1`, `hdmi2`, `dp`, `usbc`. The aliases `hdmi`, `displayport`, `usb-c`, `type-c`, and `typec` also work.

### Example: two computers, one monitor

Connect a laptop over USB-C and a desktop over DisplayPort.

- On the laptop: `msikvm set dp` gives the screen to the desktop.
- On the desktop: `msikvm set usbc` gives it back.

Both computers need a USB connection to the monitor for this to work in both directions. If the monitor's built-in KVM moves the USB upstream along with the video input, only the computer currently on screen can send commands. In that case, run the command from the computer that is currently on screen.

You can bind the command to a hotkey with Raycast, Alfred, or Shortcuts on macOS, AutoHotkey or a shortcut to [`usbc.exe`](#one-click-switch-to-usb-c) on Windows, or your desktop environment's keyboard settings on Linux.

## How it works

The monitor exposes a vendor-specific USB HID device. Each command is a 64-byte report with report ID `0x01`, followed by an ASCII command and a `\r` terminator:

| Action | Sent              | Reply                     |
| ------ | ----------------- | ------------------------- |
| Read   | `58` + setting    | `5b` + setting + value    |
| Write  | `5b` + setting + value | `5600+` on success   |

The input source is setting `00500`, and its value is a three-digit number:

| Value | Input       |
| ----- | ----------- |
| `000` | HDMI 1      |
| `001` | HDMI 2      |
| `002` | DisplayPort |
| `003` | USB-C       |

So switching to DisplayPort sends `\x01` `5b00500002` `\r`.

## Troubleshooting

- **`no MSI monitor found`**: the monitor's USB upstream cable isn't connected to this computer, or (on Linux) you need the udev rule above.
- **`monitor rejected set`**: the monitor didn't accept the value. Your model may number its inputs differently. Run `get` while on each input to find the right values.
- **Nothing happens after `set`**: some monitors ignore input changes while the OSD menu is open, or when the target input has no signal.

## Credits

The protocol was reverse-engineered by the [msigd](https://github.com/couriersud/msigd) project, a full-featured Linux tool for MSI monitor settings. This project is an independent, minimal reimplementation that only handles input switching.

## Disclaimer

This project is not affiliated with or endorsed by MSI. The monitor firmware doesn't validate commands, so sending unsupported settings can leave it in a bad state. This tool only ever writes the input-source setting. Use it at your own risk.
