"""
Command-line interface (CLI) for nexus-air.
"""

import argparse
import os
import subprocess
import sys

from nexus_air.constants import (
    BYTE_TO_RATE,
    RATE_TO_BYTE,
    LIGHT_MODES,
    DPI_EFFECTS,
    SENSOR_MODES,
    BUTTON_NAMES,
    BUTTON_ACTIONS,
    TUPLE_TO_ACTION,
    UDEV_RULE,
)
from nexus_air.protocol import calc_checksum
from nexus_air.device import find_devices, NexusAirDevice


def install_udev_rules():
    rule_path = "/etc/udev/rules.d/99-nexus-air.rules"
    if os.geteuid() != 0:
        print(f"[*] {rule_path} yazmak için root yetkisi gerekiyor (sudo)...")
        cmd = [
            "sudo", "sh", "-c",
            f"cat > {rule_path} << 'EOF'\n{UDEV_RULE}EOF\n"
            "udevadm control --reload-rules && udevadm trigger",
        ]
        subprocess.run(cmd, check=True)
    else:
        with open(rule_path, "w") as f:
            f.write(UDEV_RULE)
        subprocess.run(["udevadm", "control", "--reload-rules"], check=True)
        subprocess.run(["udevadm", "trigger"], check=True)
    print(f"[+] udev kuralı kuruldu: {rule_path}")
    print("[+] Artık Nexus Air V1 farenizi sudo olmadan kullanabilirsiniz.")


def print_status(dev: NexusAirDevice):
    online = dev.is_online()
    print(f"Cihaz     : {dev.info['name']} ({dev.info['hid_name']})")
    print(f"Yol       : {dev.path} (VID=0x{dev.info['vid']:04X}, PID=0x{dev.info['pid']:04X})")
    print(f"Durum     : {'Çevrimiçi (Online)' if online else 'Uyku Modunda / Çevrimdışı (Hareket ettirin)'}")
    try:
        ver = dev.get_version()
        print(f"Firmware  : {ver}")
    except TimeoutError:
        pass
    try:
        bat = dev.get_battery()
        chg = " (Şarj Oluyor)" if bat["charging"] else ""
        print(f"Batarya   : %{bat['level']}{chg} ({bat['voltage_mv']} mV)")
    except TimeoutError:
        pass
    if not online:
        return
    try:
        cfg = dev.read_all_settings()
    except TimeoutError as e:
        print(f"Uyarı     : {e}")
        return
    act_idx = cfg["current_dpi_stage"]
    act_dpi = cfg["dpi_stages"][act_idx]
    stages_str = ", ".join(
        f"{'*' if i == act_idx else ''}S{i+1}:{cfg['dpi_stages'][i]}({cfg['dpi_colors'][i][0]},{cfg['dpi_colors'][i][1]},{cfg['dpi_colors'][i][2]})"
        for i in range(cfg["max_dpi_stages"])
    )
    print(f"Profil    : Profil {cfg['profile'] + 1} (Donanım Bank #{cfg['profile']})")
    print(f"Aktif DPI : {act_dpi} DPI (Kademe {act_idx + 1}/{cfg['max_dpi_stages']})")
    print(f"Kademeler : {stages_str}")
    print(
        f"DPI Işığı : {DPI_EFFECTS.get(cfg['dpi_effect'], cfg['dpi_effect'])} | "
        f"Parlaklık:{cfg['dpi_brightness_level']}/10 | Nefes Hızı:{cfg['dpi_speed']}/5"
    )
    print(f"Rapor Hz  : {cfg['report_rate_hz']} Hz")
    print(f"LOD       : {cfg['lod_mm']} mm")
    print(f"Sensör Mod: {SENSOR_MODES.get(cfg['sensor_mode'], cfg['sensor_mode'])}")
    print(f"Debounce  : {cfg['debounce_ms']} ms")
    print(f"MotionSync: {'Açık' if cfg['motion_sync'] else 'Kapalı'}")
    print(f"AngleSnap : {'Açık' if cfg['angle_snapping'] else 'Kapalı'}")
    print(f"Ripple    : {'Açık' if cfg['ripple_control'] else 'Kapalı'}")
    print(f"Peak Perf : {'Açık' if cfg['peak_performance'] else 'Kapalı'} (Uyku: {cfg['sleep_sec']} sn)")
    print(
        f"RGB Şerit : {LIGHT_MODES.get(cfg['led_mode'], cfg['led_mode'])} | "
        f"RGB{cfg['led_color']} | Hız:{cfg['led_speed']+1}/8 Parlaklık:{cfg['led_brightness']+1}/10 | "
        f"Hareketle Kapat:{'Evet' if cfg['move_off_led'] else 'Hayır'} ({cfg['light_off_sec']} sn)"
    )
    print("Tuşlar    :")
    for i, bt in enumerate(cfg["buttons"]):
        _, label = TUPLE_TO_ACTION.get(bt, ("custom", f"Özel {bt}"))
        print(f"  [{i+1}] {BUTTON_NAMES[i]:20s} -> {label}")


def main():
    parser = argparse.ArgumentParser(
        prog="nexus-air",
        description="Nexus Air V1 — CachyOS / Linux Fare Yapılandırma Aracı (CLI + GTK4 GUI)"
    )
    parser.add_argument("--test", action="store_true", help="Protokol öz-testlerini çalıştır")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("gui", help="GTK4 grafik arayüzünü başlat (varsayılan)")
    sub.add_parser("status", help="Fare durumunu, bataryayı ve tüm EEPROM ayarlarını göster")
    sub.add_parser("udev", help="/dev/hidraw* için udev izin kuralını kur")
    sub.add_parser("reset", help="Fareyi fabrika ayarlarına sıfırla")
    sub.add_parser("pair", help="2.4GHz alıcı eşleştirme modunu başlat")

    p_dpi = sub.add_parser("dpi", help="DPI değerini veya kademesini ayarla")
    p_dpi.add_argument("value", type=int, help="DPI değeri (100..10000)")
    p_dpi.add_argument("--stage", type=int, default=None, help="Hedef kademe (1..6, varsayılan: aktif kademe)")
    p_dpi.add_argument("--color", type=str, default=None, help="Kademe RGB rengi, örn: 255,0,0")

    p_stage = sub.add_parser("stage", help="Aktif DPI kademesini veya toplam kademe sayısını seç")
    p_stage.add_argument("active", type=int, help="Aktif kademe (1..6)")
    p_stage.add_argument("--max", type=int, default=None, help="Toplam kademe sayısı (1..6)")

    p_rate = sub.add_parser("rate", help="Yoklama oranını (Polling Rate Hz) ayarla")
    p_rate.add_argument("hz", type=int, choices=sorted(RATE_TO_BYTE.keys()), help="Hz (125/250/500/1000/2000/4000/8000)")

    p_lod = sub.add_parser("lod", help="Kalkış mesafesini (LOD) ayarla")
    p_lod.add_argument("mm", type=int, choices=[1, 2], help="1 veya 2 mm")

    p_deb = sub.add_parser("debounce", help="Tuş debounce süresini (ms) ayarla")
    p_deb.add_argument("ms", type=int, help="Debounce süresi (0..30 ms)")

    p_ms = sub.add_parser("motionsync", help="Motion Sync aç/kapat")
    p_ms.add_argument("state", choices=["on", "off"])

    p_as = sub.add_parser("anglesnap", help="Angle Snapping (düz çizgi) aç/kapat")
    p_as.add_argument("state", choices=["on", "off"])

    p_rip = sub.add_parser("ripple", help="Ripple Control aç/kapat")
    p_rip.add_argument("state", choices=["on", "off"])

    p_peak = sub.add_parser("peak", help="Peak Performance modunu ve uyku süresini ayarla")
    p_peak.add_argument("state", choices=["on", "off"])
    p_peak.add_argument("--sleep", type=int, default=None, help="Uyku süresi (saniye, örn: 30, 60, 300)")

    p_smode = sub.add_parser("sensormode", help="Sensör güç modunu ayarla (0=LP, 1=HP, 2=Corded)")
    p_smode.add_argument("mode", type=int, choices=[0, 1, 2])

    p_led = sub.add_parser("led", help="Alt RGB şerit ve DPI gösterge aydınlatmasını ayarla")
    p_led.add_argument("mode", type=int, choices=range(6), help="0=Kapalı, 1=Rainbow, 2=Breathing, 3=Fixed, 4=Neon, 5=Flicker")
    p_led.add_argument("--rgb", type=str, default="255,0,0", help="R,G,B (örn: 255,106,0)")
    p_led.add_argument("--speed", type=int, default=4, choices=range(1, 9), help="Hız (1..8)")
    p_led.add_argument("--brightness", type=int, default=4, choices=range(1, 11), help="Parlaklık (1..10)")
    p_led.add_argument("--move-off", choices=["on", "off"], default=None, help="Hareket ederken ışığı kapat")
    p_led.add_argument("--dpi-led", type=int, choices=range(3), default=None, help="DPI Işığı: 0=Kapalı, 1=Sabit, 2=Nefes")

    p_btn = sub.add_parser("button", help="Fare tuşuna işlev ata")
    p_btn.add_argument("button_num", type=int, choices=range(1, 7), help="1=Sol, 2=Sağ, 3=Orta, 4=Geri, 5=İleri, 6=DPI")
    p_btn.add_argument("action", choices=list(BUTTON_ACTIONS.keys()), help="Atanacak işlev")

    p_prof = sub.add_parser("profile", help="Donanım profilini değiştir (1..4 veya 0..3)")
    p_prof.add_argument("index", type=int, help="Profil numarası (1..4)")

    args = parser.parse_args()

    if args.cmd == "udev":
        install_udev_rules()
        return

    if args.cmd in (None, "gui"):
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            from nexus_air.gui import launch_gui
            launch_gui()
            return
        args.cmd = "status"

    devs = find_devices()
    if not devs:
        print("[-] Nexus Air V1 bulunamadı (VID=0x3554, PID=0xF512/0xF5D5/0xF5A7).", file=sys.stderr)
        sys.exit(1)

    try:
        with NexusAirDevice(devs[0]) as dev:
            if args.cmd == "status":
                print_status(dev)
            elif args.cmd == "dpi":
                dev.set_driver_status(1)
                if args.stage is not None:
                    idx = args.stage - 1
                    dev.set_current_dpi_stage(idx)
                else:
                    raw = dev.read_flash(0x04, 2)
                    idx = raw[0] if raw[1] == calc_checksum([raw[0]]) and raw[0] < 6 else 0
                dev.set_stage_dpi(idx, args.value)
                if args.color:
                    r, g, b = [int(x) for x in args.color.split(",")]
                    dev.set_stage_color(idx, r, g, b)
                print(f"[+] Kademe {idx + 1} -> {args.value} DPI olarak ayarlandı.")
            elif args.cmd == "stage":
                dev.set_driver_status(1)
                if args.max is not None:
                    dev.set_max_dpi_stages(args.max)
                dev.set_current_dpi_stage(args.active - 1)
                print(f"[+] Aktif DPI kademesi {args.active} olarak ayarlandı.")
            elif args.cmd == "rate":
                dev.set_driver_status(1)
                dev.set_report_rate(args.hz)
                print(f"[+] Yoklama oranı (Polling Rate) {args.hz} Hz olarak ayarlandı.")
            elif args.cmd == "lod":
                dev.set_driver_status(1)
                dev.set_lod(args.mm)
                print(f"[+] LOD {args.mm} mm olarak ayarlandı.")
            elif args.cmd == "debounce":
                dev.set_driver_status(1)
                dev.set_debounce(args.ms)
                print(f"[+] Debounce süresi {args.ms} ms olarak ayarlandı.")
            elif args.cmd == "motionsync":
                dev.set_driver_status(1)
                dev.set_motion_sync(args.state == "on")
                print(f"[+] Motion Sync: {args.state}")
            elif args.cmd == "anglesnap":
                dev.set_driver_status(1)
                dev.set_angle_snapping(args.state == "on")
                print(f"[+] Angle Snapping: {args.state}")
            elif args.cmd == "ripple":
                dev.set_driver_status(1)
                dev.set_ripple_control(args.state == "on")
                print(f"[+] Ripple Control: {args.state}")
            elif args.cmd == "peak":
                dev.set_driver_status(1)
                dev.set_peak_performance(args.state == "on")
                if args.sleep is not None:
                    dev.set_sleep_time(args.sleep)
                print(f"[+] Peak Performance: {args.state}")
            elif args.cmd == "sensormode":
                dev.set_driver_status(1)
                dev.set_sensor_mode(args.mode)
                print(f"[+] Sensör modu: {SENSOR_MODES[args.mode]}")
            elif args.cmd == "led":
                dev.set_driver_status(1)
                r, g, b = [int(x) for x in args.rgb.split(",")]
                dev.set_led_bar(args.mode, r, g, b, args.speed - 1, args.brightness - 1, 1 if args.mode > 0 else 0)
                if args.dpi_led is not None:
                    dev.set_dpi_led(args.dpi_led, 0x80, 3, 1 if args.dpi_led > 0 else 0)
                if args.move_off is not None:
                    dev.set_move_off_led(args.move_off == "on")
                print(f"[+] RGB Aydınlatma -> {LIGHT_MODES[args.mode]} ({r},{g},{b}) olarak ayarlandı.")
            elif args.cmd == "button":
                if args.button_num == 1 and args.action != "left":
                    print("[-] Güvenlik: Sol tuş (1) yalnızca 'left' olarak bırakılabilir.", file=sys.stderr)
                    sys.exit(1)
                dev.set_driver_status(1)
                dev.set_button(args.button_num - 1, BUTTON_ACTIONS[args.action][1])
                print(f"[+] Tuş {args.button_num} ({BUTTON_NAMES[args.button_num-1]}) -> {BUTTON_ACTIONS[args.action][0]}")
            elif args.cmd == "profile":
                idx = args.index - 1 if 1 <= args.index <= 4 else args.index
                dev.set_profile(idx)
                print(f"[+] Aktif profil Profil {idx + 1} (Bank #{idx}) olarak değiştirildi.")
            elif args.cmd == "reset":
                dev.factory_reset()
                print("[+] Fare fabrika ayarlarına sıfırlandı.")
            elif args.cmd == "pair":
                dev.pair_dongle()
                print("[+] Alıcı eşleştirme modu başlatıldı (Sol+Orta+Sağ tuşlara basılı tutun).")
    except (PermissionError, RuntimeError, ValueError, TimeoutError) as exc:
        print(f"[-] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
