import unittest

from nexus_air.constants import REPORT_ID, PACKET_LEN, BATTERY_MV_TABLE
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


class TestNexusAirProtocol(unittest.TestCase):
    def test_checksum_and_fields(self):
        # HIDUsb.dll @ 0x18000ec10 checksum math
        self.assertEqual(calc_checksum([0x08, 0x03]), 0x4A)
        self.assertEqual(make_field([0x01]), bytes([0x01, 0x54]))
        self.assertEqual(make_field([0x00]), bytes([0x00, 0x55]))
        self.assertEqual(make_field([0x08]), bytes([0x08, 0x4D]))

    def test_packet_builder(self):
        pkt = build_packet(0x03)
        self.assertEqual(len(pkt), PACKET_LEN)
        self.assertEqual(pkt[0], REPORT_ID)
        self.assertEqual(pkt[1], 0x03)
        self.assertEqual(pkt[16], 0x4A)

        pkt_ver = build_packet(0x12)
        self.assertEqual(pkt_ver[16], 0x3B)

    def test_paw3325_dpi_roundtrip(self):
        test_dpis = [100, 400, 800, 1200, 1600, 2400, 3200, 4000, 4200, 4800, 6400, 8000, 10000]
        for dpi in test_dpis:
            vx, vy, sc = encode_dpi(dpi)
            self.assertEqual(decode_dpi(vx, vy, sc), dpi)

    def test_dpi_brightness_levels(self):
        for lvl in range(1, 11):
            raw = dpi_level_to_brightness(lvl)
            self.assertEqual(dpi_brightness_to_level(raw), lvl)

    def test_battery_interpolation(self):
        self.assertEqual(mv_to_percent(3050), 0)
        self.assertEqual(mv_to_percent(4110), 100)
        self.assertEqual(mv_to_percent(3880), 50)


if __name__ == "__main__":
    unittest.main()
