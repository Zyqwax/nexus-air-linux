"""
NexusAirDevice class providing hardware communication over /dev/hidraw*.
"""

import glob
import json
import os
import select
import sys
import time

from nexus_air.constants import (
    VID,
    PIDS,
    REPORT_ID,
    PACKET_LEN,
    BYTE_TO_RATE,
    RATE_TO_BYTE,
    PROFILE_DIR,
)
from nexus_air.protocol import (
    calc_checksum,
    make_field,
    build_packet,
    encode_dpi,
    decode_dpi,
    mv_to_percent,
    dpi_brightness_to_level,
    dpi_level_to_brightness,
)


def save_profile_backup(profile_idx: int, cfg: dict):
    """Save per-profile config JSON to ~/.config/nexus-air/profile_{0..3}.json."""
    try:
        os.makedirs(PROFILE_DIR, exist_ok=True)
        path = os.path.join(PROFILE_DIR, f"profile_{profile_idx}.json")
        with open(path, "w") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass


def find_devices() -> list[dict]:
    """Scan /sys/class/hidraw for VID 0x3554 interface with vendor Report ID 0x08."""
    found = []
    for sys_path in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        dev_name = os.path.basename(sys_path)
        uevent_path = os.path.join(sys_path, "device", "uevent")
        rdesc_path = os.path.join(sys_path, "device", "report_descriptor")
        if not os.path.exists(uevent_path):
            continue
        try:
            uevent = open(uevent_path, "r", errors="replace").read()
            rdesc = open(rdesc_path, "rb").read() if os.path.exists(rdesc_path) else b""
        except OSError:
            continue
        vid = pid = 0
        hid_name = ""
        for line in uevent.splitlines():
            if line.startswith("HID_ID="):
                parts = line.split("=")[1].split(":")
                if len(parts) == 3:
                    vid = int(parts[1], 16)
                    pid = int(parts[2], 16)
            elif line.startswith("HID_NAME="):
                hid_name = line.split("=", 1)[1]
        if vid != VID or pid not in PIDS:
            continue
        if b"\x06\x02\xff" in rdesc and b"\x85\x08" in rdesc:
            model_name, cid, mid = PIDS[pid]
            found.append({
                "path": f"/dev/{dev_name}",
                "vid": vid,
                "pid": pid,
                "name": model_name,
                "hid_name": hid_name,
                "cid": cid,
                "mid": mid,
            })
    return found


class NexusAirDevice:
    def __init__(self, dev_info: dict):
        self.info = dev_info
        self.path = dev_info["path"]
        self.fd: int | None = None

    def __enter__(self):
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)
        except PermissionError as exc:
            raise PermissionError(
                f"{self.path} erişim reddedildi.\n"
                f"Kalıcı izin için: sudo nexus-air udev\n"
                f"Veya geçici olarak komutu 'sudo' ile çalıştırın."
            ) from exc
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def _drain(self):
        while True:
            r, _, _ = select.select([self.fd], [], [], 0)
            if not r:
                break
            try:
                os.read(self.fd, 64)
            except BlockingIOError:
                break

    def xfer(self, cmd: int, addr: int = 0, data: bytes | list[int] = b"", retries: int = 3) -> bytes:
        pkt = build_packet(cmd, addr, data)
        for _ in range(retries):
            self._drain()
            os.write(self.fd, pkt)
            deadline = time.monotonic() + 0.15
            while time.monotonic() < deadline:
                rem = max(0.01, deadline - time.monotonic())
                r, _, _ = select.select([self.fd], [], [], rem)
                if not r:
                    break
                try:
                    resp = os.read(self.fd, 64)
                except BlockingIOError:
                    continue
                if len(resp) >= PACKET_LEN and resp[0] == REPORT_ID and resp[1] == (cmd & 0xFF):
                    return resp[:PACKET_LEN]
            time.sleep(0.02)
        raise TimeoutError(f"Cihaz yanıt vermedi (cmd=0x{cmd:02X}, addr=0x{addr:04X}). Fare uykuda olabilir; hareket ettirin.")

    def set_driver_status(self, active: int = 1):
        try:
            self.xfer(0x02, 0, [active & 0xFF], retries=2)
        except TimeoutError:
            pass

    def is_online(self) -> bool:
        try:
            resp = self.xfer(0x03, retries=2)
            return resp[6] > 0
        except TimeoutError:
            return False

    def get_battery(self) -> dict:
        resp = self.xfer(0x04)
        level = resp[6]
        charging = bool(resp[7])
        mv = (resp[8] << 8) | resp[9]
        if level == 0 and mv > 0:
            level = mv_to_percent(mv)
        return {"level": min(100, level), "charging": charging, "voltage_mv": mv}

    def get_version(self) -> str:
        resp = self.xfer(0x12)
        return f"v{resp[6]}.{resp[7]:02d}"

    def get_profile(self) -> int:
        resp = self.xfer(0x0E)
        return min(3, max(0, resp[6]))

    def set_profile(self, profile: int):
        if not 0 <= profile <= 3:
            raise ValueError("Profil 0..3 (veya 1..4) arasında olmalıdır")
        self.set_driver_status(1)
        self.xfer(0x0F, 0, [profile])
        time.sleep(0.04)

    def read_flash(self, addr: int, length: int) -> bytes:
        """Read EEPROM/Flash via cmd 0x08 (byte[3:4]=addr, byte[5]=chunk_len)."""
        out = bytearray()
        off = 0
        while off < length:
            chunk = min(10, length - off)
            pkt = [0] * PACKET_LEN
            pkt[0] = REPORT_ID
            pkt[1] = 0x08
            pkt[3] = ((addr + off) >> 8) & 0xFF
            pkt[4] = (addr + off) & 0xFF
            pkt[5] = chunk
            pkt[16] = calc_checksum(pkt[:16])
            raw_pkt = bytes(pkt)
            got = None
            for _ in range(3):
                self._drain()
                os.write(self.fd, raw_pkt)
                deadline = time.monotonic() + 0.15
                while time.monotonic() < deadline:
                    r, _, _ = select.select([self.fd], [], [], max(0.01, deadline - time.monotonic()))
                    if not r:
                        break
                    resp = os.read(self.fd, 64)
                    if len(resp) >= PACKET_LEN and resp[0] == REPORT_ID and resp[1] == 0x08:
                        got = resp[6 : 6 + chunk]
                        break
                if got is not None:
                    break
                time.sleep(0.02)
            if got is None:
                raise TimeoutError(f"EEPROM okuma zaman aşımı: 0x{addr + off:04X}")
            out.extend(got)
            off += chunk
        return bytes(out)

    def write_flash(self, addr: int, data: bytes | list[int]):
        """Write EEPROM/Flash via cmd 0x07 (up to 10 bytes per chunk)."""
        raw = bytes(data)
        off = 0
        while off < len(raw):
            chunk = raw[off : off + 10]
            self.xfer(0x07, addr + off, chunk, retries=3)
            off += len(chunk)

    def read_all_settings(self) -> dict:
        """Read current profile (0x0E) and 0x00..0xBA from mouse EEPROM."""
        self.set_driver_status(1)
        prof = self.get_profile()
        mem = self.read_flash(0x00, 0xBB)

        def u8(addr: int, default: int) -> int:
            val, chk = mem[addr], mem[addr + 1]
            return val if chk == calc_checksum([val]) else default

        rate_byte = u8(0x00, 0x01)
        max_dpi = max(1, min(8, u8(0x02, 6)))
        cur_dpi = u8(0x04, 1)
        if cur_dpi >= max_dpi:
            cur_dpi = 0
        lod = u8(0x0A, 1) or 1

        dpi_stages = []
        dpi_colors = []
        defaults_dpi = [400, 800, 1600, 2400, 3200, 6400, 8000, 10000]
        defaults_col = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
            (0, 255, 255), (255, 0, 255), (255, 255, 255), (255, 165, 0),
        ]
        for i in range(8):
            base = 0x0C + i * 4
            b0, b1, b2, chk = mem[base : base + 4]
            if chk == calc_checksum([b0, b1, b2]):
                dpi_stages.append(decode_dpi(b0, b1, b2))
            else:
                dpi_stages.append(defaults_dpi[i])

            cbase = 0x2C + i * 4
            r, g, b, cchk = mem[cbase : cbase + 4]
            if cchk == calc_checksum([r, g, b]):
                dpi_colors.append((r, g, b))
            else:
                dpi_colors.append(defaults_col[i])

        dpi_hw_effect = u8(0x4C, 1)
        if dpi_hw_effect not in (1, 2):
            dpi_hw_effect = 1
        dpi_bright_raw = u8(0x4E, 0x80)
        dpi_speed = max(1, min(5, u8(0x50, 3)))
        dpi_led_sw = u8(0x52, 1)
        dpi_effect_ui = 0 if dpi_led_sw == 0 else dpi_hw_effect

        buttons = []
        default_btns = [
            (0x01, 0x01, 0x00),
            (0x01, 0x02, 0x00),
            (0x01, 0x04, 0x00),
            (0x01, 0x08, 0x00),
            (0x01, 0x10, 0x00),
            (0x02, 0x01, 0x00),
        ]
        for i in range(6):
            kbase = 0x60 + i * 4
            t, p1, p2, kchk = mem[kbase : kbase + 4]
            if kchk == calc_checksum([t, p1, p2]):
                buttons.append((t, p1, p2))
            else:
                buttons.append(default_btns[i])

        led_chunk = list(mem[0xA0:0xA6])
        if mem[0xA6] == calc_checksum(led_chunk):
            l_hw_mode, l_r, l_g, l_b, l_spd, l_brt = led_chunk
        else:
            l_hw_mode, l_r, l_g, l_b, l_spd, l_brt = (1, 255, 0, 0, 3, 3)
        if not 1 <= l_hw_mode <= 5:
            l_hw_mode = 1
        l_sw = u8(0xA7, 1)
        l_mode_ui = 0 if l_sw == 0 else l_hw_mode

        cfg = {
            "profile": prof,
            "report_rate_hz": BYTE_TO_RATE.get(rate_byte, 1000),
            "max_dpi_stages": max_dpi,
            "current_dpi_stage": cur_dpi,
            "lod_mm": lod,
            "dpi_stages": dpi_stages,
            "dpi_colors": dpi_colors,
            "dpi_effect": dpi_effect_ui,
            "dpi_hw_effect": dpi_hw_effect,
            "dpi_brightness": dpi_bright_raw,
            "dpi_brightness_level": dpi_brightness_to_level(dpi_bright_raw),
            "dpi_speed": dpi_speed,
            "dpi_led_switch": dpi_led_sw,
            "buttons": buttons,
            "led_mode": l_mode_ui,
            "led_hw_mode": l_hw_mode,
            "led_color": (l_r, l_g, l_b),
            "led_speed": max(0, min(7, l_spd)),
            "led_brightness": max(0, min(9, l_brt)),
            "led_switch": l_sw,
            "debounce_ms": u8(0xA9, 8),
            "motion_sync": bool(u8(0xAB, 1)),
            "light_off_sec": u8(0xAD, 6) * 10,
            "angle_snapping": bool(u8(0xAF, 0)),
            "ripple_control": bool(u8(0xB1, 0)),
            "move_off_led": bool(u8(0xB3, 0)),
            "peak_performance": bool(u8(0xB5, 0)),
            "sleep_sec": u8(0xB7, 6) * 10,
            "sensor_mode": u8(0xB9, 0),
        }
        save_profile_backup(prof, cfg)
        return cfg

    def set_report_rate(self, hz: int):
        if hz not in RATE_TO_BYTE:
            raise ValueError(f"Desteklenen Hz değerleri: {sorted(RATE_TO_BYTE.keys())}")
        self.write_flash(0x00, make_field([RATE_TO_BYTE[hz]]))

    def set_max_dpi_stages(self, count: int):
        if not 1 <= count <= 6:
            raise ValueError("DPI kademe sayısı 1..6 arasında olmalıdır")
        self.write_flash(0x02, make_field([count]))

    def set_current_dpi_stage(self, stage_idx: int):
        if not 0 <= stage_idx <= 5:
            raise ValueError("DPI kademe indeksi 0..5 arasında olmalıdır")
        self.write_flash(0x04, make_field([stage_idx]))

    def set_lod(self, mm: int):
        if mm not in (1, 2):
            raise ValueError("LOD 1 veya 2 mm olmalıdır")
        self.write_flash(0x0A, make_field([mm]))

    def set_stage_dpi(self, stage_idx: int, dpi: int):
        if not 0 <= stage_idx <= 7:
            raise ValueError("Kademe 0..7 arasında olmalıdır")
        vx, vy, scale = encode_dpi(dpi)
        self.write_flash(0x0C + stage_idx * 4, make_field([vx, vy, scale]))

    set_Stage_dpi = set_stage_dpi

    def set_stage_color(self, stage_idx: int, r: int, g: int, b: int):
        if not 0 <= stage_idx <= 7:
            raise ValueError("Kademe 0..7 arasında olmalıdır")
        self.write_flash(0x2C + stage_idx * 4, make_field([r & 0xFF, g & 0xFF, b & 0xFF]))

    def set_dpi_led(self, effect: int, brightness: int = 0x80, speed: int = 3, switch: int | None = None):
        if switch is None:
            sw = 0 if effect == 0 else 1
        else:
            sw = 1 if (effect > 0 and switch) else 0

        if effect > 0:
            hw_eff = 1 if effect == 1 else 2
            self.write_flash(0x4C, make_field([hw_eff]))
        else:
            cur = self.read_flash(0x4C, 2)
            if cur[1] != calc_checksum([cur[0]]) or cur[0] not in (1, 2):
                self.write_flash(0x4C, make_field([1]))

        self.write_flash(0x4E, make_field([brightness & 0xFF]))
        self.write_flash(0x50, make_field([max(1, min(5, speed))]))
        self.write_flash(0x52, make_field([sw]))

    def set_button(self, btn_idx: int, action_tuple: tuple[int, int, int]):
        if not 0 <= btn_idx <= 15:
            raise ValueError("Tuş indeksi 0..15 arasında olmalıdır")
        t, p1, p2 = action_tuple
        self.write_flash(0x60 + btn_idx * 4, make_field([t & 0xFF, p1 & 0xFF, p2 & 0xFF]))

    def set_led_bar(self, mode: int, r: int, g: int, b: int, speed: int = 3, brightness: int = 3, switch: int | None = None):
        if switch is None:
            sw = 0 if mode == 0 else 1
        else:
            sw = 1 if (mode > 0 and switch) else 0

        spd = max(0, min(7, int(speed)))
        brt = max(0, min(9, int(brightness)))

        if mode > 0:
            hw_mode = max(1, min(5, int(mode)))
        else:
            cur = self.read_flash(0xA0, 7)
            hw_mode = cur[0] if (cur[6] == calc_checksum(list(cur[:6])) and 1 <= cur[0] <= 5) else 1

        bar6 = [hw_mode & 0xFF, r & 0xFF, g & 0xFF, b & 0xFF, spd & 0xFF, brt & 0xFF]
        self.write_flash(0xA0, make_field(bar6))
        self.write_flash(0xA7, make_field([sw]))

    def set_debounce(self, ms: int):
        if not 0 <= ms <= 50:
            raise ValueError("Debounce süresi 0..50 ms arasında olmalıdır")
        self.write_flash(0xA9, make_field([ms]))

    def set_motion_sync(self, enabled: bool):
        self.write_flash(0xAB, make_field([1 if enabled else 0]))

    def set_light_off_time(self, seconds: int):
        units = max(1, min(240, seconds // 10))
        self.write_flash(0xAD, make_field([units]))

    def set_angle_snapping(self, enabled: bool):
        self.write_flash(0xAF, make_field([1 if enabled else 0]))

    def set_ripple_control(self, enabled: bool):
        self.write_flash(0xB1, make_field([1 if enabled else 0]))

    def set_move_off_led(self, enabled: bool):
        self.write_flash(0xB3, make_field([1 if enabled else 0]))

    def set_peak_performance(self, enabled: bool):
        self.write_flash(0xB5, make_field([1 if enabled else 0]))

    def set_sleep_time(self, seconds: int):
        units = max(3, min(240, seconds // 10))
        self.write_flash(0xB7, make_field([units]))

    def set_sensor_mode(self, mode: int):
        if mode not in (0, 1, 2):
            raise ValueError("Sensör modu 0 (LP), 1 (HP), 2 (Corded) olmalıdır")
        self.write_flash(0xB9, make_field([mode]))

    def factory_reset(self):
        self.set_driver_status(1)
        self.xfer(0x09)
        time.sleep(0.25)
        defaults_dpi = [400, 800, 1600, 2400, 3200, 6400, 8000, 10000]
        defaults_col = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
            (0, 255, 255), (255, 0, 255), (255, 255, 255), (255, 165, 0),
        ]
        self.set_report_rate(1000)
        self.set_max_dpi_stages(4)
        self.set_current_dpi_stage(1)
        self.set_lod(1)
        for i in range(8):
            self.set_stage_dpi(i, defaults_dpi[i])
            self.set_stage_color(i, *defaults_col[i])
        self.set_dpi_led(1, 0x80, 3, 1)
        default_btns = [
            (0x01, 0x01, 0x00), (0x01, 0x02, 0x00), (0x01, 0x04, 0x00),
            (0x01, 0x08, 0x00), (0x01, 0x10, 0x00), (0x02, 0x01, 0x00),
        ]
        for i, bt in enumerate(default_btns):
            self.set_button(i, bt)
        self.set_led_bar(1, 255, 0, 0, 3, 3, 1)
        self.set_debounce(8)
        self.set_motion_sync(True)
        self.set_light_off_time(30)
        self.set_angle_snapping(False)
        self.set_ripple_control(False)
        self.set_move_off_led(False)
        self.set_peak_performance(False)
        self.set_sleep_time(60)
        self.set_sensor_mode(0)

    def pair_dongle(self):
        cid, mid = self.info["cid"], self.info["mid"]
        self.xfer(0x05, 0, [cid, mid])
