import os
import gi
import dbus
import subprocess
import locale


gi.require_version("Gtk", "3.0")

from gi.repository import GLib, Gtk
from locale import gettext as _

APPNAME_CODE = "pardus-nvidia-installer"
TRANSLATIONS_PATH = "/usr/share/locale/"
locale.bindtextdomain(APPNAME_CODE, TRANSLATIONS_PATH)
locale.textdomain(APPNAME_CODE)


def start_prc(self, params):
    print(params)
    pid, std_in, std_out, std_err = GLib.spawn_async(
        params,
        flags=GLib.SpawnFlags.DO_NOT_REAP_CHILD,
        standard_output=True,
        standard_error=True,
    )
    GLib.io_add_watch(
        GLib.IOChannel(std_out),
        GLib.IO_IN | GLib.IO_HUP,
        on_process_stdout,
        self,
    )
    pid = GLib.child_watch_add(GLib.PRIORITY_DEFAULT, pid, on_process_stdext, self)
    self.ui_main_window.set_sensitive(False)
    self.ui_status_progressbar.set_show_text(True)
    return pid


def on_process_stdout(src, cond, self):
    if cond == GLib.IO_HUP:
        return False
    line = src.readline()
    if "dlstatus" in line or "pmstatus" in line:
        splits = line.split(":")
        prc = float(splits[2])
        txt = splits[3]
        prg_frac = float(prc / 100)
        prog_txt = f"Status %{prc:.2f} :: {txt}"
        self.ui_status_progressbar.set_text(prog_txt)
        self.ui_status_progressbar.set_fraction(prg_frac)
    return True


def on_process_stderr(src, cond, ui_obj):
    if cond == GLib.IO_HUP:
        return False
    line = src.readline()
    return True


def on_process_stdext(pid, stat, self):
    print(stat)
    self.ui_status_progressbar.set_fraction(1)
    if stat == 0:
        self.ui_status_progressbar.set_text(_("Operation completed successfully"))
        if self.apt_opr != "update":
            if self.ui_confirm_dialog:
                dlg_res = self.ui_confirm_dialog.run()
                if dlg_res == Gtk.ResponseType.OK:
                    subprocess.call(
                        [
                            "dbus-send",
                            "--system",
                            "--print-reply",
                            "--dest=org.freedesktop.login1",
                            "/org/freedesktop/login1",
                            "org.freedesktop.login1.Manager.Reboot",
                            "boolean:true",
                        ]
                    )
                elif dlg_res == Gtk.ResponseType.CANCEL:
                    pass
            self.ui_confirm_dialog.destroy()
        self.create_gpu_drivers()
    if stat == 15 or stat == 32256 or stat == 32512:
        if self.apt_opr == "update":
            self.ui_repo_switch.handler_block_by_func(self.on_nvidia_mirror_changed)  
            self.ui_repo_switch.set_active(not self.ui_repo_switch.get_active())
            self.ui_repo_switch.handler_unblock_by_func(self.on_nvidia_mirror_changed)  
        self.ui_status_progressbar.set_text(_("Auth or cancellation error"))

    else:
        self.ui_status_progressbar.set_text(_("An error occured"))
    self.ui_main_window.set_sensitive(True)
