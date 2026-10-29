"""
HIDUsb protocol encoding, decoding, checksums, and packet builders.
"""

from nexus_air.constants import (
    REPORT_ID,
    PACKET_LEN,
    BATTERY_MV_TABLE,
    DPI_BRIGHTNESS_TABLE,
)


def calc_checksum(data: bytes | list[int]) -> int:
    """HIDUsb.dll @ 0x18000ec10: (0x55 - sum(data)) & 0xFF"""
    return (0x55 - (sum(data) & 0xFF)) & 0xFF


def make_field(values: list[int]) -> bytes:
    """Append EEPROM field checksum byte: values + [(0x55 - sum(values)) & 0xFF]"""
    return bytes(values + [calc_checksum(values)])


def build_packet(cmd: int, addr: int = 0, data: bytes | list[int] = b"") -> bytes:
    """Build 17-byte HID Report ID 0x08 command packet."""
    payload = list(data)
    if len(payload) > 10:
        raise ValueError("Payload max 10 bytes per packet")
    pkt = [0] * PACKET_LEN
    pkt[0] = REPORT_ID
    pkt[1] = cmd & 0xFF
    pkt[2] = 0x00
    pkt[3] = (addr >> 8) & 0xFF
    pkt[4] = addr & 0xFF
    pkt[5] = len(payload)
    for i, b in enumerate(payload):
        pkt[6 + i] = b & 0xFF
    pkt[16] = calc_checksum(pkt[:16])
    return bytes(pkt)


def encode_dpi(dpi: int) -> tuple[int, int, int]:
    """Sensor::WriteDPI @ 0x140010310 (PAW3325: 100..4000 step 100, 4200..10000 step 200)."""
    dpi = max(100, min(10000, int(dpi)))
    if dpi <= 4000:
        dpi = max(100, round(dpi / 100) * 100)
        val = (dpi // 50) - 1
        return (val & 0xFF, val & 0xFF, 0x00)
    dpi = max(4200, round(dpi / 200) * 200)
    val = (dpi // 100) - 1
    return (val & 0xFF, val & 0xFF, 0x11)


def decode_dpi(val_x: int, _val_y: int, scale: int) -> int:
    """Inverse of Sensor::WriteDPI for PAW3325."""
    if scale == 0x11:
        return (val_x + 1) * 100
    return (val_x + 1) * 50


def dpi_brightness_to_level(raw_byte: int) -> int:
    """Map EEPROM 0x4E byte (0x10..0xFF) to UI level 1..10."""
    best_idx = min(range(len(DPI_BRIGHTNESS_TABLE)), key=lambda i: abs(DPI_BRIGHTNESS_TABLE[i] - raw_byte))
    return best_idx + 1


def dpi_level_to_brightness(level: int) -> int:
    """Map UI level 1..10 to EEPROM 0x4E byte."""
    idx = max(0, min(len(DPI_BRIGHTNESS_TABLE) - 1, int(level) - 1))
    return DPI_BRIGHTNESS_TABLE[idx]


def mv_to_percent(mv: int) -> int:
    if mv <= BATTERY_MV_TABLE[0]:
        return 0
    if mv >= BATTERY_MV_TABLE[-1]:
        return 100
    for i in range(len(BATTERY_MV_TABLE) - 1):
        lo, hi = BATTERY_MV_TABLE[i], BATTERY_MV_TABLE[i + 1]
        if lo <= mv <= hi:
            return int(round((i + (mv - lo) / max(1, hi - lo)) * 5))
    return 100
