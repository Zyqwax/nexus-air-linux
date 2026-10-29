# Claw's Nexus Air V1 — Hardware & HID Protocol Specification

This document details the reverse-engineered hardware architecture, USB HID report formats, EEPROM memory mapping, and command opcodes for the **Claw's Nexus Air V1 Wireless/Wired Gaming Mouse**.

Reverse engineered using the **REA (Reverse Engineer Anything)** toolset and **Gemini 4 Argon Medium** from Windows binary drivers (`Nexus Air V1.exe`, `HIDUsb.dll`).

---

## 1. Hardware Overview

* **Brand / Model:** Claw's Technology — Nexus Air V1 Lightweight Honeycomb Gaming Mouse
* **Sensor:** PixArt PAW3325 (Optical, up to 10,000 DPI)
* **Wireless MCU / Receiver:** Compx 2.4GHz Wireless USB Transceiver
* **USB Vendor ID (VID):** `0x3554`
* **Product IDs (PID):**
  * `0xF5A7`: Nexus Air V1 Wired Mode
  * `0xF512`: Nexus Air V1 2.4G Wireless Receiver (Firmware v2.00 / Update 1)
  * `0xF5D5`: Nexus Air V1 2.4G Wireless Receiver (Update 2)
* **HID Endpoints:**
  * Endpoint 1: Standard USB Mouse (Report ID 0x01, 0x02)
  * Vendor Endpoint: Usage Page `0xFF02`, Report ID `0x08` (Packet Length: 17 bytes)

---

## 2. Packet Structure (Report ID 0x08)

All control transfers use 17-byte HID Feature/Output reports over `/dev/hidraw*`:

```
Byte 00: Report ID (0x08)
Byte 01: Command Opcode (0x02, 0x03, 0x04, 0x07, 0x08, 0x09, 0x0E, 0x0F, 0x12)
Byte 02: 0x00
Byte 03: EEPROM Address High Byte ((Addr >> 8) & 0xFF)
Byte 04: EEPROM Address Low Byte (Addr & 0xFF)
Byte 05: Payload Length (0..10 bytes)
Byte 06..15: Data payload bytes
Byte 16: Checksum: (0x55 - sum(Byte 00..15)) & 0xFF
```

### Opcodes
* `0x02`: Set Driver Status (1 = Active)
* `0x03`: Check Online Status
* `0x04`: Query Battery Status (Level %, Charging flag, Millivolts)
* `0x05`: 2.4GHz Pairing Mode
* `0x07`: Write Flash/EEPROM (up to 10 bytes per transaction)
* `0x08`: Read Flash/EEPROM (Byte 5 specifies chunk size to read)
* `0x09`: Factory Reset
* `0x0E`: Get Current Active Hardware Profile (Returns 0..3)
* `0x0F`: Set Current Hardware Profile (Payload: `[Profile_Index (0..3)]`)
* `0x12`: Query Firmware Version (`v{major}.{minor:02d}`)

---

## 3. EEPROM Memory Map (`0x00..0xBA`)

Every single parameter or block stored in mouse EEPROM is immediately followed by its own 1-byte checksum:
`Checksum = (0x55 - sum(field_bytes)) & 0xFF`.

| Address | Size | Function | Values / Format |
|---|---|---|---|
| `0x00` | 2 bytes | Polling Rate (Hz) | `0x08`=125Hz, `0x04`=250Hz, `0x02`=500Hz, `0x01`=1000Hz, `0x10`=2000Hz, `0x20`=4000Hz, `0x40`=8000Hz |
| `0x02` | 2 bytes | Total DPI Stages | `1..6` (Default: 4 or 6) |
| `0x04` | 2 bytes | Active DPI Stage Index | `0..5` (0 = Stage 1) |
| `0x0A` | 2 bytes | Lift-Off Distance (LOD) | `1` = 1mm, `2` = 2mm |
| `0x0C` | 4 bytes | DPI Stage 1 Value | PixArt encoded `(val_x, val_y, scale, chk)` |
| `0x10` | 4 bytes | DPI Stage 2 Value | PixArt encoded |
| `0x14` | 4 bytes | DPI Stage 3 Value | PixArt encoded |
| `0x18` | 4 bytes | DPI Stage 4 Value | PixArt encoded |
| `0x1C` | 4 bytes | DPI Stage 5 Value | PixArt encoded |
| `0x20` | 4 bytes | DPI Stage 6 Value | PixArt encoded |
| `0x2C` | 4 bytes | DPI Stage 1 Color | `(R, G, B, chk)` — Color displayed on mouse DPI LED |
| `0x30` | 4 bytes | DPI Stage 2 Color | `(R, G, B, chk)` |
| `0x34` | 4 bytes | DPI Stage 3 Color | `(R, G, B, chk)` |
| `0x38` | 4 bytes | DPI Stage 4 Color | `(R, G, B, chk)` |
| `0x3C` | 4 bytes | DPI Stage 5 Color | `(R, G, B, chk)` |
| `0x40` | 4 bytes | DPI Stage 6 Color | `(R, G, B, chk)` |
| `0x4C` | 2 bytes | DPI LED Effect Mode | `1` = Fixed, `2` = Breathing (Never write 0 here!) |
| `0x4E` | 2 bytes | DPI LED Brightness | `0x10, 0x1E, 0x3C, 0x5A, 0x80, 0x96, 0xB4, 0xD2, 0xF0, 0xFF` (Levels 1..10) |
| `0x50` | 2 bytes | DPI LED Breathing Speed| `1..5` |
| `0x52` | 2 bytes | DPI LED Switch | `0` = OFF, `1` = ON (To turn DPI LED off, set this to 0) |
| `0x60` | 24 bytes| Button Bindings (1-6) | 6 buttons x 4 bytes `(Type, Param1, Param2, chk)` |
| `0xA0` | 7 bytes | RGB Bottom Strip Mode | `[Mode(1..5), R, G, B, Speed(0..7), Brightness(0..9), chk]` |
| `0xA7` | 2 bytes | RGB Bottom Strip Switch| `0` = OFF, `1` = ON |
| `0xA9` | 2 bytes | Debounce Time | `0..50` milliseconds |
| `0xAB` | 2 bytes | Motion Sync | `0` = Disabled, `1` = Enabled |
| `0xAD` | 2 bytes | Inactivity Light-Off | Seconds // 10 (`1..240`, e.g. 6 = 60s) |
| `0xAF` | 2 bytes | Angle Snapping | `0` = Disabled, `1` = Enabled |
| `0xB1` | 2 bytes | Ripple Control | `0` = Disabled, `1` = Enabled |
| `0xB3` | 2 bytes | Move-Off LED | `1` = Turn off strip when moving mouse (battery saver) |
| `0xB5` | 2 bytes | Peak Performance Mode | `0` = Disabled, `1` = Enabled |
| `0xB7` | 2 bytes | Sleep Timeout | Seconds // 10 (`3..240`, e.g. 6 = 60s) |
| `0xB9` | 2 bytes | Sensor Power Mode | `0` = LP (Low Power), `1` = HP (High Perf), `2` = Corded |

---

## 4. Critical Reverse Engineering Findings

1. **Two-Packet RGB Strip Write Requirement:**
   The mouse firmware rejects turning the strip OFF if written as a single chunk at `0xA0`. To properly control the strip:
   * `0xA0` must ALWAYS receive a 7-byte packet with `Mode` between `1..5`.
   * `0xA7` must be written separately as a 2-byte packet with `[Switch (0 or 1), Checksum]`.

2. **DPI Stage LED Color Independence:**
   The DPI indicator LED does not have a single global color. Instead, its color is tied to the current active DPI stage (`0x2C..0x4B`). When the user switches DPI stages, the MCU automatically lights up that stage's specific RGB color.
