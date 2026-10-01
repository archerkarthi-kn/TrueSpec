# TrueSpec: Second-Hand Laptop Inspector 🔍💻

<p align="center">
  <img src="logo.jpg" alt="TrueSpec Banner" width="700">
</p>

[![Build TrueSpec Portable Windows Release](https://github.com/archerkarthi-kn/TrueSpec/actions/workflows/build_release.yml/badge.svg)](https://github.com/archerkarthi-kn/TrueSpec/actions/workflows/build_release.yml)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg?logo=windows)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-3776AB.svg?logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**TrueSpec** is a standalone, portable Windows diagnostic tool designed to be carried on a USB drive when inspecting and buying used laptops. 

Used laptop markets are filled with deceptive tricks: dishonest sellers frequently modify the Windows Registry to rename a Core i3 into a Core i7, conceal degraded batteries, swap motherboard serials, or flash BIOSes on fake graphics cards. TrueSpec cuts through the operating system's cosmetic facade to extract ground-truth hardware silicon signatures, calculate true battery wear, verify S.M.A.R.T. disk health, and generate an actionable buyer's negotiation score.

---

## ⚡ The Threat Model: Deceptions Caught by TrueSpec

| Scam / Hardware Defect | How Dishonest Sellers Hide It | How TrueSpec Catches It |
| :--- | :--- | :--- |
| **CPU Registry Spoofing** | Modifying `HKLM\HARDWARE\DESCRIPTION\System\CentralProcessor\0\ProcessorNameString` in the registry to make Task Manager & "About PC" show a fake tier (e.g. i3 renamed to i7). | Executes the x86 `CPUID` instruction directly on the silicon die via hardware registers and compares it with the registry and core topology. Flags **🚨 REGISTRY SPOOF DETECTED** and drops score to `0/100`. |
| **Masked Battery Degradation** | Battery shows "100%" in the taskbar, concealing that the maximum capacity has shrunk to 40% of factory spec. | Executes Windows `powercfg /batteryreport /xml`, extracts factory `DesignCapacity` vs actual `FullChargeCapacity`, and calculates exact **Wear Level %** and **Cycle Count**. |
| **Failing Storage Drives** | Formatted drives can look fast and empty, hiding catastrophic impending mechanical or flash failures. | Inspects hardware S.M.A.R.T. health flags (`Status == OK` vs `Pred Fail`) and identifies whether the OS drive is an NVMe SSD, SATA SSD, or slow HDD. |
| **Fake / Flashed GPUs** | Subsystem BIOS flashed with generic IDs or overclocked mobile chips masquerading as higher tiers. | Queries WMI `Win32_VideoController` for true hardware VRAM and un-spoofable PCI PNP Device IDs (`PCI\VEN_...&DEV_...`). |
| **Swapped / Refurbished Motherboards** | Broken laptops repaired with low-grade or stolen boards with wiped serials. | Reads `Win32_BIOS` Serial and `Win32_ComputerSystemProduct` UUID and prompts the buyer to cross-reference with the physical chassis barcode label. Flags placeholder serials like *"To be filled by O.E.M."*. |
| **Dead Pixels & Backlight Bleed** | Panel damage, dead subpixels, or edge-light bleeding masked by default wallpaper. | Built-in borderless fullscreen test engine cycling pure Red, Green, Blue, White, Black, 50% Gray, and subpixel spectrums. |

---

## 🌟 Key Features

- **🛡️ Anti-Spoof CPU Verification Engine:** Direct silicon CPUID inspection vs Windows Registry & core topology.
- **🔋 Deep Battery Health & Wear Analysis:** Automated `powercfg` XML runner and wear level calculator.
- **🧠 RAM Architecture & Channel Map:** Displays total RAM, populated slots vs total slots on motherboard (e.g. *"2 of 2 slots used"*), speed (MHz), and Single vs Dual-Channel mode.
- **💾 Storage & S.M.A.R.T. Health:** Instant detection of NVMe SSDs, SATA SSDs, and HDDs, with S.M.A.R.T. failure prediction.
- **🎮 GPU Inspection:** Real VRAM and unforgeable PCI Vendor & Device IDs.
- **🔍 Motherboard & Chassis Serial Verification:** Cross-reference hardware firmware serials against physical case stickers.
- **💡 Smart Buyer Verdict & Negotiation Engine (0–100 Score):**
  - `🟢 SAFE TO BUY` (80–100 pts)
  - `🟡 BUY WITH NEGOTIATION` (55–79 pts)
  - `🔴 DO NOT BUY / HIGH RISK` (<55 pts or critical red flags)
  - Actionable price negotiation arguments and exact upgrade cost estimates.
- **🖥️ Fullscreen Dead Pixel Tester:** Interactive LCD inspection with 9 solid color planes (Spacebar/Click to cycle, Esc to exit).
- **📄 One-Click Export (HTML & TXT):** Generates print-ready, high-contrast inspection reports viewable in any browser or notepad.
- **🔒 100% Offline & Non-Invasive:** Zero internet required, zero registry modifications, zero permanent files left behind.

---

## 🚀 Quick Start (Running from USB)

1. Download the pre-compiled `TrueSpec_Inspector.exe` from the [GitHub Releases](https://github.com/archerkarthi-kn/TrueSpec/releases) tab.
2. Copy `TrueSpec_Inspector.exe` to your USB flash drive.
3. Plug the USB drive into the laptop you are inspecting.
4. Double-click `TrueSpec_Inspector.exe`:
   - TrueSpec will automatically perform the full audit within 2–3 seconds.
   - Review the **Overall Verdict** and **Buyer Suggestions**.
   - Click **🖥️ Dead Pixel Tester** to check the LCD.
   - Click **📄 Export Inspection Report** to save a permanent timestamped copy (`.html` and `.txt`) directly to your USB drive!

---

## 🛠️ Running from Source (Developer Setup)

### Prerequisites
- Windows 10 or Windows 11 (x64)
- Python 3.10+ (tested on Python 3.12 and 3.13)

### Installation

```powershell
# 1. Clone repository
git clone https://github.com/archerkarthi-kn/TrueSpec.git
cd TrueSpec

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run TrueSpec Inspector
python src/main.py
```

---

## 📦 Compiling Standalone Single-File `.exe`

To build your own portable `.exe` using PyInstaller:

```powershell
# Activate your virtual environment first
.\venv\Scripts\Activate.ps1

# Compile with PyInstaller
pyinstaller --noconfirm --onefile --windowed `
  --name TrueSpec_Inspector `
  --icon assets/icon.ico `
  --collect-all customtkinter `
  --add-data "src;src" `
  --add-data "assets;assets" `
  src/main.py
```

The resulting standalone executable will be generated at:
```text
dist\TrueSpec_Inspector.exe
```

---

## 📂 Project Architecture

```text
TRUESPEC/
├── .github/
│   └── workflows/
│       └── build_release.yml      # Automated GitHub Actions workflow to build portable .exe
├── src/
│   ├── main.py                    # CustomTkinter dark-mode GUI dashboard & background thread runner
│   ├── hardware_audit.py          # Anti-spoof CPU, RAM slots, Disk S.M.A.R.T., GPU, and BIOS serials
│   ├── battery_audit.py           # powercfg battery report runner, XML parser, and wear calculator
│   ├── recommendation_engine.py   # 0-100 scoring algorithm, red-flag detector, and negotiation advice
│   ├── report_exporter.py         # Print-ready HTML and ASCII TXT report generator
│   └── screen_keyboard_test.py    # Borderless fullscreen dead-pixel & backlight bleed color cycler
├── requirements.txt               # customtkinter, psutil, py-cpuinfo, wmi, pywin32, pyinstaller
├── .gitignore                     # Clean ignore rules for builds, reports, and caches
└── README.md                      # Comprehensive buyer guide and technical documentation
```

---

## ⚖️ Scoring & Buyer Negotiation Rules

| Condition | Score Impact | Buyer Action / Negotiation Point |
| :--- | :---: | :--- |
| **CPU Registry Spoof Detected** | **Immediate 0 / 100** | **WALK AWAY.** Fraudulent seller modified registry. |
| **S.M.A.R.T. Disk Health Failure** | **Capped at ≤ 20** | **DO NOT BUY.** Storage drive is failing; imminent data loss. |
| **Battery Health < 60%** | **-25 pts** | Demand a $40–$80 discount to cover a battery replacement. |
| **Battery Health 60%–79%** | **-10 pts** | Moderate battery wear; negotiate a 5–10% discount off asking price. |
| **Battery Cycles > 500** | **-5 pts** | Battery has undergone heavy charge cycling. |
| **Installed RAM < 8GB** | **-15 pts** | Negotiate $20–$30 discount to install an additional 8GB stick. |
| **Single-Channel Memory Active** | **-5 pts** | Bandwidth bottleneck; check for an empty slot to enable dual-channel. |
| **Primary Drive is Mechanical HDD**| **-20 pts** | System lacks an SSD; deduct $30–$70 for an NVMe/SATA SSD upgrade. |
| **Generic BIOS / Chassis Serial** | **-5 pts** | Motherboard was swapped, flashed, or refurbished; verify bottom case sticker. |

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
