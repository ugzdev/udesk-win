<div align="center">
  <img src="images/app_icon_000.png" alt="uDesk Logo" width="110">

  <h1>uDesk PC</h1>

  <p><b>A local network bridge connecting your Windows PC and Android device for remote control, system monitoring, and custom macro execution.</b></p>
  <p><sub>Developed by <b>UGZ</b></sub></p>

  <br>

  <p>
    <a href="PLAY_STORE_LINK_HERE">
      <img src="https://img.shields.io/badge/Get%20it%20on-Google%20Play-414141?style=for-the-badge&logo=googleplay&logoColor=3DDC84" alt="Get it on Google Play">
    </a>
    <a href="GITHUB_RELEASE_LINK_HERE">
      <img src="https://img.shields.io/badge/Download-Windows%20Server-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Download for Windows">
    </a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue?style=flat-square">
    <img src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white">
  </p>
</div>

<br>

---

## What's uDesk?

uDesk is a local network bridge between your Windows PC and your Android device, made up of a Windows server app running quietly in your system tray and a companion Android app that turns your phone into a full remote control hub. Together they give you a low-latency wireless touchpad and remote keyboard, live CPU/RAM/network monitoring, per-app audio mixing, two-way clipboard sync, live media playback sync with playback controls, remote app/website launching, screen capture streaming, and a fully customizable JSON-based macro deck (built with the desktop Mod Editor) that shows up as tappable button decks on your phone.

<div align="center">

<img src="images/screenshots/0.png" width="480"><br>
<sub><b>Main Dashboard</b></sub>
<br>

<hr width="40%">

<img src="images/screenshots/1.png" width="480"><br>
<sub><b>Android Homepage</b></sub>
<br>

<hr width="40%">

<img src="images/screenshots/2.png" width="480"><br>
<sub><b>Settings Dialog</b></sub>
<br>

<hr width="40%">

<img src="images/screenshots/3.png" width="480"><br>
<sub><b>uDesk Browser</b></sub>
<br>

<hr width="40%">

<img src="images/screenshots/4.png" width="480"><br>
<sub><b>About uDesk Dialog</b></sub>

</div>

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup & Connection](#setup--connection)
- [Mod Editor: Custom Macro Deck](#mod-editor-custom-macro-deck)
- [Ports & Security](#ports--security)
- [Troubleshooting](#troubleshooting)

---

## Features

### Input Control
uDesk provides a two-way input model between your PC and Android device:

* **Android → PC (Touchpad):** Use your Android device as a low-latency wireless touchpad. Movement and click data are streamed straight to the PC over a dedicated UDP socket, so there's no noticeable lag.
* **PC → Android (Input Forwarding):** Press **`Ctrl + Shift + Alt`** anywhere on your PC to instantly lock the system cursor (it gets centered and hidden), and every further mouse movement, scroll, and keystroke is captured and forwarded live to the Android app. This turns your phone into a remote keyboard/mouse for the PC. Press the same hotkey again to release control and give your PC's input back to Windows.

### Application & Media Management
* **App Launcher:** Add `.exe` executables, `.lnk` shortcuts, or folder/shell paths to the PC dashboard. They instantly show up on your Android device for one-tap remote launching.
* **Advanced Audio Mixer:** Goes beyond a single master volume slider, since uDesk lists every active Windows audio session (per running app) so you can mute or adjust individual app volumes straight from your phone.

### Dashboard Customization & Sync
* **Android Wallpaper Setup:** Browse a local image on your PC; uDesk encodes and pushes it as the Android app's background, so both ends match visually.
* **Media / URL Preview:** Paste an image or GIF URL on the PC dashboard to display it as a live widget on the Android side.
* **Live Media Sync:** Automatically detects the currently playing media title, artist, and album art via the Windows System Media Transport Controls API and pushes it to your phone in real time, with play/pause, next, and previous controls included.

### Utilities & Productivity
* **Screen Capture Snipping:** A frameless, click-and-drag snipping tool captures any region of your screen and sends it straight to your Android device.
* **System Monitoring:** Streams live CPU usage, RAM allocation, and network throughput (Mbps) to the mobile client roughly every 1.5 seconds.
* **Clipboard Synchronization:** Detects PC clipboard changes and pushes them to Android automatically, and also accepts clipboard text pasted from the mobile app back onto the PC.
* **System Tray Integration:** uDesk minimizes to the system tray instead of closing, so the server keeps running in the background. Double-click the tray icon to bring the dashboard back.

---

## Requirements

uDesk PC currently supports **Windows 10/11 only**, since it relies on Windows-specific APIs (WinRT media controls, `pycaw` for per-app audio sessions, Win32 cursor/input hooks).

If you're running from source rather than the packaged release, you'll need Python 3.9+ and the following packages:

```
PyQt5
PyQtWebEngine (optional, only if you build from the extension bridge)
pywinrt / winrt-Windows.Media.Control
pycaw
comtypes
keyboard
pynput
psutil
pyautogui
pyperclip
pycryptodome
```

> ⚠️ Both `keyboard` and the cursor-lock features register global, low-level hooks and require the app to run **with administrator privileges** on most systems, otherwise hotkeys or forwarded keystrokes may silently fail.

---

## Third-Party Software & Licenses

uDesk uses the following third-party software and resources:

### Android Debug Bridge (ADB) for USB Cable Mode (Zero-Latency)

uDesk uses Android Debug Bridge (ADB) to communicate with Android devices (USB Cable Mode). ADB is part of the Android SDK Platform-Tools provided by Google. Due to licensing restrictions, these binaries are not bundled with the uDesk PC application. 

If you want to use the ultra-low latency USB connection, you need to add these files manually to the application's working directory:

1. **Download Platform-Tools:** Visit the official [Android SDK Platform-Tools page](https://developer.android.com/tools/releases/platform-tools) and download the ZIP package for Windows.
2. **Extract Required Files:** Open the downloaded ZIP file and extract **only** the following three files:
   * `adb.exe`
   * `AdbWinApi.dll`
   * `AdbWinUsbApi.dll`
3. **Place in Working Directory:** Copy these three files and paste them directly into the folder where your `uDesk.exe` (or `uDesk.pyw` if running from source) is located. 
4. **Connect & Restart:** Connect your Android device to your PC via USB (ensure USB Debugging is enabled on your phone), and restart the uDesk PC server. uDesk will automatically detect the ADB files and establish the wired bridge.

### Lucide Icons

uDesk uses [Lucide](https://lucide.dev/) for its SVG icon gallery and icon resources.

Lucide is licensed under the ISC License. Some Lucide icons are derived from Feather Icons and are distributed under the MIT License.

- Lucide: https://github.com/lucide-icons/lucide
- License: https://github.com/lucide-icons/lucide/blob/main/LICENSE

## Setup & Connection

1. **Run the Server:** Launch the `uDesk` executable (or `uDesk.pyw` from source) on your Windows machine. It opens the dashboard and also drops an icon in your system tray. Closing the window just minimizes it there, and the server keeps running until you quit it from the tray menu.
2. **Network Requirements:** Make sure both your PC and Android device are connected to the **same local network (LAN/Wi-Fi)**. uDesk does not work over the internet or across different networks/VPNs.
3. **Pairing:**
   * The dashboard displays your automatically detected **Server IP** and a randomly generated 6-character **Security Token** (regenerated once per install, stored locally).
   * Open the uDesk Android app, enter both values, and tap save.
4. **Firewall:** On first launch, Windows Defender Firewall may prompt you to allow uDesk network access. Accept it, otherwise the Android app won't be able to reach the PC.

<div align="center">
  <img src="images/pairing.png" alt="Pairing Process" width="750">
  <br>
  <i>Pairing process.</i>
</div>

---

## Mod Editor: Custom Macro Deck

The **Mod Editor** is a separate window used to design the button decks ("mods") that appear on your Android app, build entirely on JSON files stored locally. Open it by clicking the **`MODS`** button in the top-right corner of the main uDesk dashboard.

<div align="center">
  <img src="images/mod_editor.png" alt="Mod Editor Interface" width="750">
  <br>
  <i>The built-in editor for creating custom macros and button layouts.</i>
</div>

### 1. Creating a mod
* Click **`+ New Mod`** in the left sidebar to start a blank deck, or select an existing `.json` file from the list to edit it.
* Give it a **File Name** (saved as `mods/your_name.json`) and a display **Title**, which is what shows up as the deck's name inside the Android app.

### 2. Adding and configuring buttons
Click **`+ Add Button`** to append a new button to the deck. Each button has:

| Field | What it does |
|---|---|
| **Type** | `Title` shows the button's text label; `Icon (SVG)` shows a vector icon instead, pasted as raw `<svg>...</svg>` code into the box below. |
| **LED Indicator** | Marks this button as a toggle/status button. If its action returns an on/off state (e.g. mute status), Android lights up an indicator dot on the button. |
| **Button title** | The label shown when using `Title` type, and the tooltip/name used elsewhere. |
| **ID** | A unique identifier (`btn_1`, `btn_2`...) used internally to match the button to its action, so keep these unique within a mod. |
| **▲ / ▼** | Reorders the button up or down within the deck. |
| **✕** | Deletes the button. |

### 3. Finding an icon
Click **`Find SVG Icon`** in the sidebar to open the built-in **Lucide icon gallery**. Search by keyword, click any icon to copy its SVG code straight to your clipboard, then paste it into the button's SVG box. Icons are cached locally after the first download, so the gallery works offline afterward.

### 4. Choosing what a button does
Every button needs an **Action to Trigger**, selected from the dropdown:

1. **System Control:** pick a built-in system command: Mute/Unmute Audio, Mute/Unmute Microphone, Sleep, Lock, Shut Down, or Restart.
2. **Trigger Shortcut:** fires a keyboard shortcut on the PC, e.g. `ctrl+shift+s`. Use the same syntax as the Python `keyboard` library (keys joined with `+`).
3. **Open App/Folder:** browse and pick any executable, shortcut, or folder path; pressing the button launches it remotely.
4. **Open Website:** opens a URL in your choice of browser (Default, Chrome, Edge, Opera, Firefox), with an option to open it in a private/incognito window.
5. **Play Audio:** plays a sound file from the local `sounds/` folder on the PC (drop your `.mp3`/`.wav` files there, then hit **Refresh** in the dropdown to pick them up).

### 5. Saving and syncing to Android
* Click **`Save (JSON)`** to write the mod to disk. This is what actually persists your changes, so closing the editor without saving discards them.
* Back on the main uDesk dashboard, click **`Sync`** to push the updated mods, apps, and wallpaper to your connected Android device immediately, instead of waiting for its next automatic refresh.
* To remove a mod entirely, hover over it in the sidebar list and click the **✕** next to its name.

---

## Ports & Security

uDesk opens the following local ports, so make sure your firewall/router doesn't block them on your LAN:

| Port | Protocol | Purpose |
|---|---|---|
| `5050` | TCP | Main data channel: system stats, media info, clipboard, mods, app control, run commands |
| `5051` | HTTP | Browser-extension bridge (media/URL widgets sent from a companion browser extension) |
| `5052` | UDP | Touchpad channel: low-latency mouse movement/click packets from Android |

Every request must include the **Security Token** shown on the dashboard; requests with a missing or incorrect token are rejected. Because there's no additional transport encryption, treat uDesk as a **trusted-LAN-only** tool, and don't expose these ports to the public internet or untrusted networks (e.g. public Wi-Fi, port-forwarding through your router).

---

## Troubleshooting

* **Android app can't find the PC:** Confirm both devices are on the same Wi-Fi network (not on a guest network or separate VLAN), and that Windows Firewall has allowed uDesk through.
* **Hotkeys / forwarded keystrokes don't work:** Run uDesk as Administrator, since global keyboard hooks on Windows generally require elevated privileges.
* **Audio mixer shows no apps:** Only apps with an active audio session appear; open/play something in the app first.
* **Added app doesn't launch:** Re-check the path in the App Launcher, since moved or renamed executables/shortcuts will fail silently.