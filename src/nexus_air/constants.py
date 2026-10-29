"""
Hardware constants, VID/PIDs, and opcode definitions for Claw's Nexus Air V1.
"""

import os

VID = 0x3554
PIDS = {
    0xF5A7: ("Nexus Air V1 (Kablolu)", 0, 0),
    0xF512: ("Nexus Air V1 2.4G Alıcı (Update 1)", 0, 0),
    0xF5D5: ("Nexus Air V1 2.4G Alıcı (Update 2)", 79, 9),
}
REPORT_ID = 0x08
PACKET_LEN = 17

RATE_TO_BYTE = {125: 0x08, 250: 0x04, 500: 0x02, 1000: 0x01, 2000: 0x10, 4000: 0x20, 8000: 0x40}
BYTE_TO_RATE = {v: k for k, v in RATE_TO_BYTE.items()}

# lamplight.obj & FunctionSet::SetLightMode
LIGHT_MODES = {
    0: "Kapalı (OFF)",
    1: "Akan Gökkuşağı (Rainbow Moving)",
    2: "Tek Renk Nefes (Single Color Breathing)",
    3: "Sabit Renk (Single Fixed)",
    4: "Neon",
    5: "Çok Renkli Nefes (Rainbow Flicker)",
}

# sensoreffect.obj & FunctionSet::SetDPIEffect
DPI_EFFECTS = {0: "Kapalı (OFF)", 1: "Sabit (Fixed)", 2: "Nefes (Breathing)"}
DPI_BRIGHTNESS_TABLE = [0x10, 0x1E, 0x3C, 0x5A, 0x80, 0x96, 0xB4, 0xD2, 0xF0, 0xFF]

SENSOR_MODES = {0: "LP (Düşük Güç)", 1: "HP (Yüksek Performans)", 2: "Corded (Kablolu Oyun)"}

BUTTON_NAMES = {
    0: "Sol Tuş (Left)",
    1: "Sağ Tuş (Right)",
    2: "Orta Tuş (Middle)",
    3: "Geri Tuşu (Back)",
    4: "İleri Tuşu (Forward)",
    5: "DPI Tuşu (DPI)",
}

BUTTON_ACTIONS = {
    "disabled": ("Devre Dışı", (0x00, 0x00, 0x00)),
    "left": ("Sol Tık", (0x01, 0x01, 0x00)),
    "right": ("Sağ Tık", (0x01, 0x02, 0x00)),
    "middle": ("Orta Tık", (0x01, 0x04, 0x00)),
    "back": ("Geri", (0x01, 0x08, 0x00)),
    "forward": ("İleri", (0x01, 0x10, 0x00)),
    "dpi-loop": ("DPI Döngüsü", (0x02, 0x01, 0x00)),
    "dpi+": ("DPI+", (0x02, 0x02, 0x00)),
    "dpi-": ("DPI-", (0x02, 0x03, 0x00)),
    "scroll-left": ("Sola Kaydır", (0x03, 0x01, 0x00)),
    "scroll-right": ("Sağa Kaydır", (0x03, 0x02, 0x00)),
    "rate-switch": ("Hz Değiştir", (0x07, 0x00, 0x00)),
    "led-toggle": ("Tüm Işıklar Aç/Kapat", (0x08, 0x00, 0x00)),
    "dpi-led-toggle": ("DPI Işığı Aç/Kapat", (0x08, 0x01, 0x00)),
    "strip-led-toggle": ("Şerit Işığı Aç/Kapat", (0x08, 0x04, 0x00)),
    "profile-switch": ("Profil Değiştir", (0x09, 0x00, 0x00)),
    "play-pause": ("Oynat/Duraklat", (0x0A, 0x02, 0x00)),
    "next-track": ("Sonraki Parça", (0x0A, 0x03, 0x00)),
    "prev-track": ("Önceki Parça", (0x0A, 0x04, 0x00)),
    "mute": ("Sessiz", (0x0A, 0x06, 0x00)),
    "vol-up": ("Ses Aç", (0x0A, 0x07, 0x00)),
    "vol-down": ("Ses Kıs", (0x0A, 0x08, 0x00)),
    "scroll-up": ("Yukarı Kaydır", (0x0B, 0x01, 0x00)),
    "scroll-down": ("Aşağı Kaydır", (0x0B, 0x02, 0x00)),
}
TUPLE_TO_ACTION = {v[1]: (k, v[0]) for k, v in BUTTON_ACTIONS.items()}

BATTERY_MV_TABLE = [
    3050, 3420, 3480, 3540, 3600, 3660, 3720, 3760, 3800, 3840,
    3880, 3920, 3940, 3960, 3980, 4000, 4020, 4040, 4060, 4080, 4110,
]

UDEV_RULE = (
    '# Nexus Air V1 Wireless/Wired Gaming Mouse (Compx / Claw\'s Technology)\n'
    'KERNEL=="hidraw*", ATTRS{idVendor}=="3554", ATTRS{idProduct}=="f512", MODE="0666", TAG+="uaccess"\n'
    'KERNEL=="hidraw*", ATTRS{idVendor}=="3554", ATTRS{idProduct}=="f5d5", MODE="0666", TAG+="uaccess"\n'
    'KERNEL=="hidraw*", ATTRS{idVendor}=="3554", ATTRS{idProduct}=="f5a7", MODE="0666", TAG+="uaccess"\n'
)

PROFILE_DIR = os.path.expanduser("~/.config/nexus-air")
