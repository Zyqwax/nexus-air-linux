"""
GTK4 graphical control center for Nexus Air V1.
"""

import subprocess

from nexus_air.constants import (
    LIGHT_MODES,
    DPI_EFFECTS,
    BUTTON_NAMES,
    BUTTON_ACTIONS,
    TUPLE_TO_ACTION,
    UDEV_RULE,
)
from nexus_air.protocol import (
    dpi_level_to_brightness,
)
from nexus_air.device import (
    find_devices,
    NexusAirDevice,
)


def launch_gui():
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk, Gdk, GLib

    try:
        def _log_writer(level, fields, _user_data):
            return GLib.LogWriterOutput.HANDLED
        GLib.log_set_writer_func(_log_writer, None)
    except Exception:
        pass

    app = Gtk.Application(application_id="org.cachyos.NexusAirV1")

    def on_activate(application):
        display = Gdk.Display.get_default()
        if display is not None:
            css = Gtk.CssProvider()
            css.load_from_string(
                "scrollbar slider, scrollbar.horizontal slider, scale slider, switch slider {\n"
                "  min-width: 12px;\n"
                "  min-height: 12px;\n"
                "  margin: 0px;\n"
                "  border-width: 0px;\n"
                "}\n"
            )
            Gtk.StyleContext.add_provider_for_display(
                display, css, Gtk.STYLE_PROVIDER_PRIORITY_USER + 200
            )

        win = Gtk.ApplicationWindow(application=application)
        win.set_title("Nexus Air V1 — CachyOS Kontrol Merkezi")
        win.set_default_size(740, 680)

        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root_box.set_margin_top(14)
        root_box.set_margin_bottom(14)
        root_box.set_margin_start(14)
        root_box.set_margin_end(14)
        win.set_child(root_box)

        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl_status = Gtk.Label(label="Cihaz aranıyor...", xalign=0)
        lbl_status.set_hexpand(True)

        top_box.append(lbl_status)
        top_box.append(Gtk.Label(label="Profil:"))
        dd_profile = Gtk.DropDown.new_from_strings(["Profil 1", "Profil 2", "Profil 3", "Profil 4"])
        top_box.append(dd_profile)

        btn_refresh = Gtk.Button(label="Yenile")
        btn_udev = Gtk.Button(label="udev İzni")
        top_box.append(btn_refresh)
        top_box.append(btn_udev)
        root_box.append(top_box)

        notebook = Gtk.Notebook()
        notebook.set_vexpand(True)
        root_box.append(notebook)

        # TAB 1: DPI & Sensör
        tab_sensor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab_sensor.set_margin_top(12)
        tab_sensor.set_margin_start(12)
        tab_sensor.set_margin_end(12)
        notebook.append_page(tab_sensor, Gtk.Label(label="DPI ve Sensör"))

        row_stage = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row_stage.append(Gtk.Label(label="Aktif DPI Kademesi (1-6):"))
        sp_cur_stage = Gtk.SpinButton.new_with_range(1, 6, 1)
        row_stage.append(sp_cur_stage)
        row_stage.append(Gtk.Label(label="Toplam Kademe (1-6):"))
        sp_max_stage = Gtk.SpinButton.new_with_range(1, 6, 1)
        row_stage.append(sp_max_stage)
        tab_sensor.append(row_stage)

        color_dialog = Gtk.ColorDialog() if hasattr(Gtk, "ColorDialog") else None
        dpi_spins = []
        stage_rgb_spins = []
        stage_color_btns = []

        def _make_rgba(r_val: int, g_val: int, b_val: int):
            rgba = Gdk.RGBA()
            rgba.red = max(0, min(255, int(r_val))) / 255.0
            rgba.green = max(0, min(255, int(g_val))) / 255.0
            rgba.blue = max(0, min(255, int(b_val))) / 255.0
            rgba.alpha = 1.0
            return rgba

        state = {"updating_ui": False}

        for i in range(6):
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl = Gtk.Label(label=f"Kademe {i+1} DPI:", width_chars=13, xalign=0)
            sp = Gtk.SpinButton.new_with_range(100, 10000, 100)
            r.append(lbl)
            r.append(sp)
            r.append(Gtk.Label(label="  DPI Işık Rengi:"))
            sr = Gtk.SpinButton.new_with_range(0, 255, 5)
            sg = Gtk.SpinButton.new_with_range(0, 255, 5)
            sb = Gtk.SpinButton.new_with_range(0, 255, 5)
            if color_dialog is not None:
                cbtn = Gtk.ColorDialogButton.new(color_dialog)
                r.append(cbtn)
                stage_color_btns.append(cbtn)

                def _on_stage_cbtn(btn, _pspec, spins=(sr, sg, sb)):
                    if state["updating_ui"]:
                        return
                    rgba = btn.get_rgba()
                    state["updating_ui"] = True
                    spins[0].set_value(round(rgba.red * 255))
                    spins[1].set_value(round(rgba.green * 255))
                    spins[2].set_value(round(rgba.blue * 255))
                    state["updating_ui"] = False

                def _on_stage_spin(_sp, btn=cbtn, spins=(sr, sg, sb)):
                    if state["updating_ui"]:
                        return
                    state["updating_ui"] = True
                    btn.set_rgba(_make_rgba(spins[0].get_value(), spins[1].get_value(), spins[2].get_value()))
                    state["updating_ui"] = False

                cbtn.connect("notify::rgba", _on_stage_cbtn)
                sr.connect("value-changed", _on_stage_spin)
                sg.connect("value-changed", _on_stage_spin)
                sb.connect("value-changed", _on_stage_spin)
            r.append(sr)
            r.append(sg)
            r.append(sb)
            tab_sensor.append(r)
            dpi_spins.append(sp)
            stage_rgb_spins.append((sr, sg, sb))

        grid_perf = Gtk.Grid(column_spacing=12, row_spacing=8)
        tab_sensor.append(grid_perf)

        rates = ["125", "250", "500", "1000", "2000", "4000"]
        dd_rate = Gtk.DropDown.new_from_strings(rates)
        grid_perf.attach(Gtk.Label(label="Yoklama Oranı (Hz):", xalign=0), 0, 0, 1, 1)
        grid_perf.attach(dd_rate, 1, 0, 1, 1)

        dd_lod = Gtk.DropDown.new_from_strings(["1 mm", "2 mm"])
        grid_perf.attach(Gtk.Label(label="LOD (Kalkış Mesafesi):", xalign=0), 2, 0, 1, 1)
        grid_perf.attach(dd_lod, 3, 0, 1, 1)

        sp_debounce = Gtk.SpinButton.new_with_range(0, 30, 1)
        grid_perf.attach(Gtk.Label(label="Debounce Süresi (ms):", xalign=0), 0, 1, 1, 1)
        grid_perf.attach(sp_debounce, 1, 1, 1, 1)

        dd_smode = Gtk.DropDown.new_from_strings(["LP (Düşük Güç)", "HP (Yüksek Performans)", "Corded (Kablolu)"])
        grid_perf.attach(Gtk.Label(label="Sensör Modu:", xalign=0), 2, 1, 1, 1)
        grid_perf.attach(dd_smode, 3, 1, 1, 1)

        sp_sleep = Gtk.SpinButton.new_with_range(30, 1800, 30)
        grid_perf.attach(Gtk.Label(label="Uyku Süresi (sn):", xalign=0), 0, 2, 1, 1)
        grid_perf.attach(sp_sleep, 1, 2, 1, 1)

        chk_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        chk_msync = Gtk.CheckButton(label="Motion Sync")
        chk_asnap = Gtk.CheckButton(label="Angle Snapping")
        chk_ripple = Gtk.CheckButton(label="Ripple Control")
        chk_peak = Gtk.CheckButton(label="Peak Performance")
        for c in (chk_msync, chk_asnap, chk_ripple, chk_peak):
            chk_box.append(c)
        tab_sensor.append(chk_box)

        # TAB 2: RGB Aydınlatma
        tab_led = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        tab_led.set_margin_top(12)
        tab_led.set_margin_start(12)
        tab_led.set_margin_end(12)
        notebook.append_page(tab_led, Gtk.Label(label="RGB Aydınlatma"))

        lbl_strip_hdr = Gtk.Label(label="1. Alt RGB Şerit Aydınlatması (0xA0 / 0xA7)", xalign=0)
        tab_led.append(lbl_strip_hdr)

        grid_led = Gtk.Grid(column_spacing=12, row_spacing=8)
        tab_led.append(grid_led)

        dd_lmode = Gtk.DropDown.new_from_strings([LIGHT_MODES[i] for i in range(6)])
        grid_led.attach(Gtk.Label(label="Şerit Modu:", xalign=0), 0, 0, 1, 1)
        grid_led.attach(dd_lmode, 1, 0, 1, 1)

        sp_r = Gtk.SpinButton.new_with_range(0, 255, 5)
        sp_g = Gtk.SpinButton.new_with_range(0, 255, 5)
        sp_b = Gtk.SpinButton.new_with_range(0, 255, 5)
        rgb_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        strip_color_btn = None
        if color_dialog is not None:
            strip_color_btn = Gtk.ColorDialogButton.new(color_dialog)
            rgb_row.append(strip_color_btn)

            def _on_strip_cbtn(btn, _pspec):
                if state["updating_ui"]:
                    return
                rgba = btn.get_rgba()
                state["updating_ui"] = True
                sp_r.set_value(round(rgba.red * 255))
                sp_g.set_value(round(rgba.green * 255))
                sp_b.set_value(round(rgba.blue * 255))
                state["updating_ui"] = False

            def _on_strip_spin(_sp):
                if state["updating_ui"]:
                    return
                state["updating_ui"] = True
                strip_color_btn.set_rgba(_make_rgba(sp_r.get_value(), sp_g.get_value(), sp_b.get_value()))
                state["updating_ui"] = False

            strip_color_btn.connect("notify::rgba", _on_strip_cbtn)
            sp_r.connect("value-changed", _on_strip_spin)
            sp_g.connect("value-changed", _on_strip_spin)
            sp_b.connect("value-changed", _on_strip_spin)

        for lbl_c, sp_c in (("R:", sp_r), ("G:", sp_g), ("B:", sp_b)):
            rgb_row.append(Gtk.Label(label=lbl_c))
            rgb_row.append(sp_c)
        grid_led.attach(Gtk.Label(label="Şerit Rengi (Mod 2 ve 3 için):", xalign=0), 0, 1, 1, 1)
        grid_led.attach(rgb_row, 1, 1, 1, 1)

        sp_lspd = Gtk.SpinButton.new_with_range(1, 8, 1)
        grid_led.attach(Gtk.Label(label="Şerit Efekt Hızı (1-8):", xalign=0), 0, 2, 1, 1)
        grid_led.attach(sp_lspd, 1, 2, 1, 1)

        sp_lbrt = Gtk.SpinButton.new_with_range(1, 10, 1)
        grid_led.attach(Gtk.Label(label="Şerit Parlaklığı (1-10):", xalign=0), 0, 3, 1, 1)
        grid_led.attach(sp_lbrt, 1, 3, 1, 1)

        sp_loff = Gtk.SpinButton.new_with_range(10, 1800, 10)
        grid_led.attach(Gtk.Label(label="Hareketsizlikte Işık Kapanma (sn):", xalign=0), 0, 4, 1, 1)
        grid_led.attach(sp_loff, 1, 4, 1, 1)

        chk_move_off = Gtk.CheckButton(label="Fare hareket ederken şerit ışığını kapat (Güç tasarrufu)")
        tab_led.append(chk_move_off)

        lbl_dpi_hdr = Gtk.Label(
            label="2. DPI Kademe Gösterge Işığı (Her kademenin rengi 'DPI ve Sensör' sekmesinden seçilir)",
            xalign=0,
        )
        tab_led.append(lbl_dpi_hdr)

        grid_dpiled = Gtk.Grid(column_spacing=12, row_spacing=8)
        tab_led.append(grid_dpiled)

        dd_dpi_eff = Gtk.DropDown.new_from_strings([DPI_EFFECTS[i] for i in range(3)])
        grid_dpiled.attach(Gtk.Label(label="DPI Işığı Modu:", xalign=0), 0, 0, 1, 1)
        grid_dpiled.attach(dd_dpi_eff, 1, 0, 1, 1)

        sp_dpi_brt = Gtk.SpinButton.new_with_range(1, 10, 1)
        grid_dpiled.attach(Gtk.Label(label="DPI Işığı Parlaklığı (1-10):", xalign=0), 0, 1, 1, 1)
        grid_dpiled.attach(sp_dpi_brt, 1, 1, 1, 1)

        sp_dpi_spd = Gtk.SpinButton.new_with_range(1, 5, 1)
        grid_dpiled.attach(Gtk.Label(label="DPI Nefes Hızı (1-5):", xalign=0), 0, 2, 1, 1)
        grid_dpiled.attach(sp_dpi_spd, 1, 2, 1, 1)

        btn_all_leds_off = Gtk.Button(label="Tüm Işıkları Hemen Kapat (Şerit + DPI LED)")
        tab_led.append(btn_all_leds_off)

        # TAB 3: Tuş Atamaları
        tab_btns = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        tab_btns.set_margin_top(12)
        tab_btns.set_margin_start(12)
        tab_btns.set_margin_end(12)
        notebook.append_page(tab_btns, Gtk.Label(label="Tuş Atamaları"))

        action_keys = list(BUTTON_ACTIONS.keys())
        action_labels = [BUTTON_ACTIONS[k][0] for k in action_keys]
        btn_dropdowns = []
        grid_btns = Gtk.Grid(column_spacing=12, row_spacing=8)
        tab_btns.append(grid_btns)
        for i in range(6):
            grid_btns.attach(Gtk.Label(label=BUTTON_NAMES[i] + ":", xalign=0), 0, i, 1, 1)
            dd = Gtk.DropDown.new_from_strings(action_labels)
            grid_btns.attach(dd, 1, i, 1, 1)
            btn_dropdowns.append(dd)

        bot_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_apply = Gtk.Button(label="Ayarları Fareye Kaydet (Uygula)")
        btn_apply.set_hexpand(True)
        btn_reset = Gtk.Button(label="Fabrika Ayarlarına Sıfırla")
        bot_box.append(btn_apply)
        bot_box.append(btn_reset)
        root_box.append(bot_box)

        def load_from_device(*_args):
            devs = find_devices()
            if not devs:
                lbl_status.set_text("Nexus Air V1 bulunamadı! Alıcıyı veya kabloyu kontrol edin.")
                return
            state["updating_ui"] = True
            try:
                with NexusAirDevice(devs[0]) as dev:
                    online = dev.is_online()
                    bat = dev.get_battery()
                    ver = dev.get_version()
                    chg = "⚡" if bat["charging"] else ""
                    if not online:
                        lbl_status.set_text(
                            f"{dev.info['name']} | {ver} | Batarya: %{bat['level']}{chg} | Uykuda (Fareyi oynatın)"
                        )
                        return
                    cfg = dev.read_all_settings()
                    dd_profile.set_selected(cfg["profile"])
                    lbl_status.set_text(
                        f"{dev.info['name']} | {ver} | Profil {cfg['profile']+1} | "
                        f"Batarya: %{bat['level']}{chg} ({bat['voltage_mv']}mV) | Çevrimiçi"
                    )
                    sp_cur_stage.set_value(cfg["current_dpi_stage"] + 1)
                    sp_max_stage.set_value(cfg["max_dpi_stages"])
                    for i in range(6):
                        dpi_spins[i].set_value(cfg["dpi_stages"][i])
                        sr, sg, sb = stage_rgb_spins[i]
                        cr, cg, cb = cfg["dpi_colors"][i]
                        sr.set_value(cr)
                        sg.set_value(cg)
                        sb.set_value(cb)
                        if i < len(stage_color_btns):
                            stage_color_btns[i].set_rgba(_make_rgba(cr, cg, cb))
                    hz_str = str(cfg["report_rate_hz"])
                    if hz_str in rates:
                        dd_rate.set_selected(rates.index(hz_str))
                    dd_lod.set_selected(0 if cfg["lod_mm"] == 1 else 1)
                    sp_debounce.set_value(cfg["debounce_ms"])
                    dd_smode.set_selected(min(2, cfg["sensor_mode"]))
                    sp_sleep.set_value(cfg["sleep_sec"])
                    chk_msync.set_active(cfg["motion_sync"])
                    chk_asnap.set_active(cfg["angle_snapping"])
                    chk_ripple.set_active(cfg["ripple_control"])
                    chk_peak.set_active(cfg["peak_performance"])

                    dd_lmode.set_selected(min(5, cfg["led_mode"]))
                    lr, lg, lb = cfg["led_color"]
                    sp_r.set_value(lr)
                    sp_g.set_value(lg)
                    sp_b.set_value(lb)
                    if strip_color_btn is not None:
                        strip_color_btn.set_rgba(_make_rgba(lr, lg, lb))
                    sp_lspd.set_value(cfg["led_speed"] + 1)
                    sp_lbrt.set_value(cfg["led_brightness"] + 1)
                    sp_loff.set_value(cfg["light_off_sec"])
                    chk_move_off.set_active(cfg["move_off_led"])

                    dd_dpi_eff.set_selected(min(2, cfg["dpi_effect"]))
                    sp_dpi_brt.set_value(cfg["dpi_brightness_level"])
                    sp_dpi_spd.set_value(cfg["dpi_speed"])

                    for i in range(6):
                        act_key, _ = TUPLE_TO_ACTION.get(cfg["buttons"][i], ("left", ""))
                        if act_key in action_keys:
                            btn_dropdowns[i].set_selected(action_keys.index(act_key))
            except Exception as e:
                lbl_status.set_text(f"Okuma hatası: {e}")
            finally:
                state["updating_ui"] = False

        def on_profile_changed(dropdown, _pspec):
            if state["updating_ui"]:
                return
            devs = find_devices()
            if not devs:
                return
            new_prof = dropdown.get_selected()
            try:
                with NexusAirDevice(devs[0]) as dev:
                    dev.set_profile(new_prof)
                load_from_device()
                lbl_status.set_text(f"Profil {new_prof + 1} aktif edildi ve fare belleğinden yüklendi.")
            except Exception as e:
                lbl_status.set_text(f"Profil değiştirme hatası: {e}")

        def apply_to_device(*_args):
            devs = find_devices()
            if not devs:
                lbl_status.set_text("Cihaz bağlı değil!")
                return
            try:
                with NexusAirDevice(devs[0]) as dev:
                    dev.set_driver_status(1)
                    prof = dd_profile.get_selected()
                    dev.set_profile(prof)

                    max_st = int(sp_max_stage.get_value())
                    cur_st = min(max_st, int(sp_cur_stage.get_value())) - 1
                    dev.set_max_dpi_stages(max_st)
                    dev.set_current_dpi_stage(cur_st)
                    for i in range(6):
                        dev.set_stage_dpi(i, int(dpi_spins[i].get_value()))
                        sr, sg, sb = stage_rgb_spins[i]
                        dev.set_stage_color(i, int(sr.get_value()), int(sg.get_value()), int(sb.get_value()))

                    hz = int(rates[dd_rate.get_selected()])
                    dev.set_report_rate(hz)
                    dev.set_lod(1 if dd_lod.get_selected() == 0 else 2)
                    dev.set_debounce(int(sp_debounce.get_value()))
                    dev.set_sensor_mode(dd_smode.get_selected())
                    dev.set_sleep_time(int(sp_sleep.get_value()))
                    dev.set_motion_sync(chk_msync.get_active())
                    dev.set_angle_snapping(chk_asnap.get_active())
                    dev.set_ripple_control(chk_ripple.get_active())
                    dev.set_peak_performance(chk_peak.get_active())

                    lmode = dd_lmode.get_selected()
                    dev.set_led_bar(
                        lmode,
                        int(sp_r.get_value()),
                        int(sp_g.get_value()),
                        int(sp_b.get_value()),
                        int(sp_lspd.get_value()) - 1,
                        int(sp_lbrt.get_value()) - 1,
                        1 if lmode > 0 else 0,
                    )
                    dev.set_light_off_time(int(sp_loff.get_value()))
                    dev.set_move_off_led(chk_move_off.get_active())

                    dpi_eff = dd_dpi_eff.get_selected()
                    dev.set_dpi_led(
                        dpi_eff,
                        dpi_level_to_brightness(int(sp_dpi_brt.get_value())),
                        int(sp_dpi_spd.get_value()),
                        1 if dpi_eff > 0 else 0,
                    )

                    for i in range(6):
                        k = action_keys[btn_dropdowns[i].get_selected()]
                        if i == 0 and k != "left":
                            k = "left"
                            btn_dropdowns[0].set_selected(action_keys.index("left"))
                        dev.set_button(i, BUTTON_ACTIONS[k][1])

                    dev.read_all_settings()
                lbl_status.set_text(f"Profil {prof + 1} ayarları fareye başarıyla kaydedildi!")
            except Exception as e:
                lbl_status.set_text(f"Yazma hatası: {e}")

        def turn_all_leds_off(*_args):
            devs = find_devices()
            if not devs:
                return
            try:
                with NexusAirDevice(devs[0]) as dev:
                    dev.set_driver_status(1)
                    dev.set_led_bar(0, int(sp_r.get_value()), int(sp_g.get_value()), int(sp_b.get_value()))
                    dev.set_dpi_led(0, dpi_level_to_brightness(int(sp_dpi_brt.get_value())), int(sp_dpi_spd.get_value()), 0)
                state["updating_ui"] = True
                dd_lmode.set_selected(0)
                dd_dpi_eff.set_selected(0)
                state["updating_ui"] = False
                lbl_status.set_text("Hem alt RGB şerit hem de DPI gösterge ışığı kapatıldı.")
            except Exception as e:
                lbl_status.set_text(f"Işık kapatma hatası: {e}")

        def reset_device(*_args):
            devs = find_devices()
            if not devs:
                return
            try:
                with NexusAirDevice(devs[0]) as dev:
                    dev.factory_reset()
                load_from_device()
                lbl_status.set_text("Aktif profil fabrika ayarlarına sıfırlandı.")
            except Exception as e:
                lbl_status.set_text(f"Sıfırlama hatası: {e}")

        def on_udev(*_args):
            try:
                subprocess.run([
                    "pkexec", "sh", "-c",
                    f"cat > /etc/udev/rules.d/99-nexus-air.rules << 'EOF'\n{UDEV_RULE}EOF\n"
                    "udevadm control --reload-rules && udevadm trigger",
                ], check=True)
                load_from_device()
            except Exception as e:
                lbl_status.set_text(f"udev kurulumu başarısız: {e}")

        dd_profile.connect("notify::selected", on_profile_changed)
        btn_refresh.connect("clicked", load_from_device)
        btn_apply.connect("clicked", apply_to_device)
        btn_all_leds_off.connect("clicked", turn_all_leds_off)
        btn_reset.connect("clicked", reset_device)
        btn_udev.connect("clicked", on_udev)

        GLib.idle_add(load_from_device)
        win.present()

    app.connect("activate", on_activate)
    app.run([])


def main():
    launch_gui()


if __name__ == "__main__":
    main()
