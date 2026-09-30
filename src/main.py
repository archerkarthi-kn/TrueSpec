"""
TrueSpec: Second-Hand Laptop Inspector
Module: main.py
Author: TrueSpec Core Systems Team

Modern Dark-Mode GUI Dashboard built with CustomTkinter.
Runs comprehensive hardware anti-spoof checks, battery wear analysis,
S.M.A.R.T. health, GPU inspection, and produces buyer advice and reports.
"""

import os
import sys
import threading
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Add local directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from hardware_audit import get_full_hardware_audit
from battery_audit import get_battery_audit
from recommendation_engine import evaluate_laptop
from report_exporter import export_both_reports, open_in_browser
from screen_keyboard_test import launch_screen_test


# Set CustomTkinter theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TrueSpecApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TrueSpec: Second-Hand Laptop Inspector v1.0")
        self.geometry("1140x840")
        self.minsize(980, 700)

        # Application state
        self.hardware_data = {}
        self.battery_data = {}
        self.eval_data = {}
        self.latest_html_report = ""
        self.latest_txt_report = ""
        self.is_scanning = False

        self._setup_ui()

        # Bind mousewheel globally across all child widgets so scrolling is 100% fluid anywhere
        self.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")

        # Start initial background scan after UI draws
        self.after(300, self.start_background_scan)

    def _on_global_mousewheel(self, event):
        """Enables smooth, lag-free scrolling across all child widgets & cards."""
        if hasattr(self, "scroll_frame") and hasattr(self.scroll_frame, "_parent_canvas"):
            try:
                if self.scroll_frame.winfo_exists():
                    delta = event.delta
                    if delta != 0:
                        # Smooth, responsive 2-unit scroll per notch (works on both mouse & precision touchpad)
                        units = int(-1 * (delta / 40))
                        if units == 0:
                            units = -1 if delta > 0 else 1
                        self.scroll_frame._parent_canvas.yview_scroll(units, "units")
            except Exception:
                pass

    def _setup_ui(self):
        # Configure root layout
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # -------------------------------------------------------------
        # TOP HEADER
        # -------------------------------------------------------------
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#0F172A", height=70)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_columnconfigure(1, weight=1)

        # App Title & Badge
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, padx=20, pady=12, sticky="w")

        title_label = ctk.CTkLabel(
            title_box,
            text="TRUESPEC",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#38BDF8"
        )
        title_label.pack(side="left")

        usb_badge = ctk.CTkLabel(
            title_box,
            text="USB PORTABLE EDITION",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#F8FAFC",
            fg_color="#0284C7",
            corner_radius=6,
            padx=8,
            pady=2
        )
        usb_badge.pack(side="left", padx=10)

        subtitle = ctk.CTkLabel(
            title_box,
            text="Second-Hand Laptop Diagnostic & Anti-Spoof Inspector",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        subtitle.pack(side="left", padx=5)

        # Header Action Buttons
        actions_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        actions_box.grid(row=0, column=2, padx=20, pady=12, sticky="e")

        self.btn_rescan = ctk.CTkButton(
            actions_box,
            text="⚡ Re-Scan Machine",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            width=150,
            height=36,
            command=self.start_background_scan
        )
        self.btn_rescan.pack(side="right", padx=5)

        # -------------------------------------------------------------
        # MAIN SCROLLABLE CONTENT AREA
        # -------------------------------------------------------------
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#0B132B", corner_radius=0)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Verdict / Score Banner
        self.verdict_frame = ctk.CTkFrame(self.scroll_frame, corner_radius=12, fg_color="#1E293B", border_width=1, border_color="#334155")
        self.verdict_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 10))
        self.verdict_frame.grid_columnconfigure(0, weight=1)

        # Verdict left info
        self.verdict_left = ctk.CTkFrame(self.verdict_frame, fg_color="transparent")
        self.verdict_left.grid(row=0, column=0, padx=20, pady=16, sticky="w")

        self.lbl_verdict_badge = ctk.CTkLabel(
            self.verdict_left,
            text="ANALYZING SYSTEM...",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#38BDF8"
        )
        self.lbl_verdict_badge.pack(anchor="w")

        self.lbl_verdict_title = ctk.CTkLabel(
            self.verdict_left,
            text="Gathering CPU silicon signatures, battery wear records, and disk S.M.A.R.T. data...",
            font=ctk.CTkFont(size=14),
            text_color="#CBD5E1"
        )
        self.lbl_verdict_title.pack(anchor="w", pady=(4, 0))

        self.lbl_system_meta = ctk.CTkLabel(
            self.verdict_left,
            text="Scanning hardware...",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        self.lbl_system_meta.pack(anchor="w", pady=(4, 0))

        # Verdict right score box
        self.score_box = ctk.CTkFrame(self.verdict_frame, corner_radius=10, fg_color="#0F172A", border_width=2, border_color="#38BDF8", width=140, height=85)
        self.score_box.grid(row=0, column=1, padx=20, pady=16, sticky="e")
        self.score_box.grid_propagate(False)

        self.lbl_score_num = ctk.CTkLabel(
            self.score_box,
            text="--",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#38BDF8"
        )
        self.lbl_score_num.pack(pady=(8, 0))

        self.lbl_score_sub = ctk.CTkLabel(
            self.score_box,
            text="SCORE / 100",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#94A3B8"
        )
        self.lbl_score_sub.pack()

        # Scanning Progress Indicator
        self.progress_bar = ctk.CTkProgressBar(self.scroll_frame, mode="indeterminate", height=6)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.progress_bar.start()

        # -------------------------------------------------------------
        # DETAIL CARDS CONTAINER
        # -------------------------------------------------------------
        self.cards_container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.cards_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=0)
        self.cards_container.grid_columnconfigure(0, weight=1)
        self.cards_container.grid_columnconfigure(1, weight=1)

        # 1. CPU Anti-Spoof Card
        self.card_cpu = self._create_card(self.cards_container, 0, 0, "🛡️ Anti-Spoof CPU Verification", columnspan=2)

        # 2. Battery Health Card
        self.card_bat = self._create_card(self.cards_container, 1, 0, "🔋 Battery Health & Wear Analysis")

        # 3. RAM Architecture Card
        self.card_ram = self._create_card(self.cards_container, 1, 1, "🧠 RAM & Memory Architecture")

        # 4. Storage & SMART Card
        self.card_storage = self._create_card(self.cards_container, 2, 0, "💾 Storage Drives & S.M.A.R.T.")

        # 5. GPU & Display Card
        self.card_gpu = self._create_card(self.cards_container, 2, 1, "🎮 Graphics & Display Adapters")

        # 6. Chassis & BIOS Serial Card
        self.card_bios = self._create_card(self.cards_container, 3, 0, "🔍 Chassis & BIOS Serial Match", columnspan=2)

        # 7. Smart Buyer Advice Card
        self.card_advice = self._create_card(self.cards_container, 4, 0, "💡 Buyer Suggestions & Negotiation Strategy", columnspan=2)

        # -------------------------------------------------------------
        # BOTTOM ACTION BAR
        # -------------------------------------------------------------
        self.footer_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#0F172A", height=60)
        self.footer_frame.grid(row=2, column=0, sticky="ew", padx=0, pady=0)
        self.footer_frame.grid_columnconfigure(1, weight=1)

        # Left status
        self.lbl_status = ctk.CTkLabel(
            self.footer_frame,
            text="Initial scan starting...",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        self.lbl_status.grid(row=0, column=0, padx=20, pady=12, sticky="w")

        # Right buttons
        btn_box = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        btn_box.grid(row=0, column=2, padx=20, pady=10, sticky="e")

        self.btn_pixel = ctk.CTkButton(
            btn_box,
            text="🖥️ Dead Pixel Tester",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#475569",
            hover_color="#334155",
            width=160,
            command=self.open_dead_pixel_tester
        )
        self.btn_pixel.pack(side="left", padx=6)

        self.btn_export = ctk.CTkButton(
            btn_box,
            text="📄 Export Inspection Report",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            width=190,
            command=self.export_reports
        )
        self.btn_export.pack(side="left", padx=6)

        self.btn_browser = ctk.CTkButton(
            btn_box,
            text="🌐 Open in Browser",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            width=150,
            state="disabled",
            command=self.view_in_browser
        )
        self.btn_browser.pack(side="left", padx=6)

    def _create_card(self, parent, row, col, title, columnspan=1):
        """Helper to create a stylized dark card container."""
        card = ctk.CTkFrame(
            parent,
            corner_radius=10,
            fg_color="#1E293B",
            border_width=1,
            border_color="#334155"
        )
        card.grid(row=row, column=col, columnspan=columnspan, sticky="nsew", padx=6, pady=6)
        card.grid_columnconfigure(0, weight=1)

        # Card header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))

        title_lbl = ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#F8FAFC"
        )
        title_lbl.pack(side="left")

        # Content frame inside card
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        content.grid_columnconfigure(0, weight=1)

        card.content = content
        card.header = header
        return card

    def start_background_scan(self):
        """Launches the system audit in a non-blocking background thread."""
        if self.is_scanning:
            return
        self.is_scanning = True
        self.btn_rescan.configure(state="disabled", text="Scanning...")
        self.progress_bar.grid()
        self.progress_bar.start()
        self.lbl_status.configure(text="Auditing hardware silicon signatures, battery wear, and S.M.A.R.T. health...")

        thread = threading.Thread(target=self._run_scan_thread, daemon=True)
        thread.start()

    def _run_scan_thread(self):
        """Thread worker executing hardware & battery audits."""
        try:
            hw = get_full_hardware_audit()
            bat = get_battery_audit()
            eval_res = evaluate_laptop(hw, bat)

            # Auto-generate temporary reports for immediate viewing
            html_p, txt_p = export_both_reports(hw, bat, eval_res, output_dir=os.getcwd())

            self.hardware_data = hw
            self.battery_data = bat
            self.eval_data = eval_res
            self.latest_html_report = html_p
            self.latest_txt_report = txt_p

            self.after(0, self._on_scan_success)
        except Exception as e:
            self.after(0, lambda: self._on_scan_error(str(e)))

    def _on_scan_success(self):
        """Callback executed on main GUI thread when scan finishes."""
        self.is_scanning = False
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.btn_rescan.configure(state="normal", text="⚡ Re-Scan Machine")
        self.btn_browser.configure(state="normal")
        self.lbl_status.configure(
            text=f"Last scanned: {datetime.datetime.now().strftime('%H:%M:%S')} • Report auto-generated: {os.path.basename(self.latest_html_report)}"
        )
        self._populate_ui()

    def _on_scan_error(self, err_msg):
        """Callback for scan failure."""
        self.is_scanning = False
        self.progress_bar.stop()
        self.progress_bar.grid_remove()
        self.btn_rescan.configure(state="normal", text="⚡ Re-Scan Machine")
        self.lbl_status.configure(text=f"Scan error: {err_msg}")
        messagebox.showerror("Scan Error", f"An error occurred during system audit:\n{err_msg}")

    def _populate_ui(self):
        """Populates all dashboard cards with telemetry data."""
        hw = self.hardware_data
        bat = self.battery_data
        ev = self.eval_data

        cpu = hw.get("cpu", {})
        ram = hw.get("ram", {})
        storage = hw.get("storage", {})
        gpu = hw.get("gpu", {})
        system = hw.get("system", {})

        # -------------------------------------------------------------
        # 1. VERDICT & SCORE
        # -------------------------------------------------------------
        score = ev.get("score", 0)
        badge = ev.get("verdict_badge", "INSPECTION COMPLETE")
        level = ev.get("verdict_level", "SAFE")
        title = ev.get("verdict_title", "")

        self.lbl_verdict_badge.configure(text=badge)
        self.lbl_verdict_title.configure(text=title)
        self.lbl_system_meta.configure(
            text=f"System: {system.get('vendor', '')} {system.get('model_name', 'Laptop')} | Chassis Serial: {system.get('chassis_serial', 'N/A')}"
        )
        self.lbl_score_num.configure(text=str(score))

        if level == "SAFE":
            score_color = "#10B981"
            border_color = "#059669"
        elif level == "NEGOTIATE":
            score_color = "#F59E0B"
            border_color = "#D97706"
        else:
            score_color = "#EF4444"
            border_color = "#DC2626"

        self.score_box.configure(border_color=border_color)
        self.lbl_score_num.configure(text_color=score_color)
        self.lbl_verdict_badge.configure(text_color=score_color)

        # -------------------------------------------------------------
        # 2. CPU ANTI-SPOOF CARD
        # -------------------------------------------------------------
        self._clear_frame(self.card_cpu.content)
        is_spoofed = cpu.get("spoof_detected", False)

        # Header status pill
        for w in self.card_cpu.header.winfo_children():
            if getattr(w, "_is_pill", False):
                w.destroy()

        status_text = "🚨 REGISTRY SPOOF DETECTED" if is_spoofed else "✅ VERIFIED GENUINE SILICON"
        status_color = "#EF4444" if is_spoofed else "#10B981"
        pill = ctk.CTkLabel(
            self.card_cpu.header,
            text=status_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=status_color,
            corner_radius=6,
            padx=8,
            pady=2
        )
        pill._is_pill = True
        pill.pack(side="right")

        # If spoofed, show prominent red alert box
        if is_spoofed:
            alert_box = ctk.CTkFrame(self.card_cpu.content, fg_color="#7F1D1D", corner_radius=8, border_width=1, border_color="#EF4444")
            alert_box.pack(fill="x", pady=(0, 10), padx=2)
            alert_lbl = ctk.CTkLabel(
                alert_box,
                text="⚠️ CRITICAL ALERT: Windows Registry CPU model string does not match silicon CPUID hardware signature!\n"
                     "The seller may have tampered with the registry to disguise an inferior processor.",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#FEE2E2",
                justify="left"
            )
            alert_lbl.pack(padx=12, pady=8, anchor="w")

        # CPU Comparison Grid
        cpu_grid = ctk.CTkFrame(self.card_cpu.content, fg_color="#0F172A", corner_radius=8)
        cpu_grid.pack(fill="x", pady=2)
        cpu_grid.grid_columnconfigure(1, weight=1)

        self._add_kv_row(cpu_grid, 0, "Windows Registry String:", cpu.get("registry_name", "N/A"), is_code=True, highlight=is_spoofed)
        self._add_kv_row(cpu_grid, 1, "Hardware CPUID Silicon:", cpu.get("cpuid_name", "N/A"), is_code=True, color="#38BDF8")
        self._add_kv_row(cpu_grid, 2, "WMI Processor Driver:", cpu.get("wmi_name", "N/A"))
        topo_str = f"{cpu.get('physical_cores', 0)} Physical Cores / {cpu.get('logical_threads', 0)} Logical Threads | L3 Cache: {round(cpu.get('l3_cache_kb', 0)/1024, 1)} MB"
        self._add_kv_row(cpu_grid, 3, "Core & Thread Topology:", topo_str)

        # -------------------------------------------------------------
        # 3. BATTERY HEALTH CARD
        # -------------------------------------------------------------
        self._clear_frame(self.card_bat.content)
        has_bat = bat.get("has_battery", False)
        if has_bat:
            b_health = bat.get("health_percent", 0.0)
            b_wear = bat.get("wear_level_percent", 0.0)
            b_design = bat.get("design_capacity_mwh", 0)
            b_full = bat.get("full_charge_capacity_mwh", 0)
            b_cycles = bat.get("cycle_count", 0)
            b_chem = bat.get("chemistry", "Unknown")
            plugged_str = "Plugged into AC" if bat.get("is_plugged") else "On Battery Power"

            # Progress Bar
            p_val = min(1.0, max(0.0, b_health / 100.0))
            p_color = "#10B981" if b_health >= 80 else ("#F59E0B" if b_health >= 60 else "#EF4444")

            bar_box = ctk.CTkFrame(self.card_bat.content, fg_color="transparent")
            bar_box.pack(fill="x", pady=(2, 6))

            lbl_bar = ctk.CTkLabel(
                bar_box,
                text=f"Battery Health: {b_health}% (Wear Level: {b_wear}%)",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=p_color
            )
            lbl_bar.pack(anchor="w")

            prog = ctk.CTkProgressBar(bar_box, height=12, progress_color=p_color, fg_color="#334155")
            prog.pack(fill="x", pady=(4, 8))
            prog.set(p_val)

            # Metrics
            bat_grid = ctk.CTkFrame(self.card_bat.content, fg_color="#0F172A", corner_radius=8)
            bat_grid.pack(fill="x", pady=2)
            bat_grid.grid_columnconfigure(1, weight=1)

            self._add_kv_row(bat_grid, 0, "Full Charge Capacity:", f"{b_full:,} mWh")
            self._add_kv_row(bat_grid, 1, "Factory Design Capacity:", f"{b_design:,} mWh")
            self._add_kv_row(bat_grid, 2, "Cycle Count:", f"{b_cycles} Cycles")
            self._add_kv_row(bat_grid, 3, "Chemistry & Status:", f"{b_chem} ({plugged_str})")
        else:
            no_bat_box = ctk.CTkFrame(self.card_bat.content, fg_color="#0F172A", corner_radius=8)
            no_bat_box.pack(fill="both", expand=True, pady=4)
            lbl = ctk.CTkLabel(
                no_bat_box,
                text="No battery detected.\nMachine is running on AC wall power (Desktop / VM / Removed Battery).",
                font=ctk.CTkFont(size=12),
                text_color="#94A3B8",
                justify="center"
            )
            lbl.pack(padx=16, pady=20)

        # -------------------------------------------------------------
        # 4. RAM ARCHITECTURE CARD
        # -------------------------------------------------------------
        self._clear_frame(self.card_ram.content)
        ram_grid = ctk.CTkFrame(self.card_ram.content, fg_color="#0F172A", corner_radius=8)
        ram_grid.pack(fill="x", pady=2)
        ram_grid.grid_columnconfigure(1, weight=1)

        self._add_kv_row(ram_grid, 0, "Installed Capacity:", f"{ram.get('total_gb', 0)} GB RAM")
        self._add_kv_row(ram_grid, 1, "Slot Configuration:", f"{ram.get('slots_used', 0)} of {ram.get('slots_total', 0)} slots used")
        self._add_kv_row(ram_grid, 2, "Channel Mode:", ram.get("channel_mode", "Single-Channel"), color="#38BDF8")

        # Sticks list
        sticks = ram.get("sticks", [])
        if sticks:
            sticks_box = ctk.CTkFrame(self.card_ram.content, fg_color="#0F172A", corner_radius=8)
            sticks_box.pack(fill="x", pady=(6, 2))
            for idx, s in enumerate(sticks):
                lbl = ctk.CTkLabel(
                    sticks_box,
                    text=f"• Slot {idx+1}: {s.get('capacity_gb', 0)}GB @ {s.get('speed_mhz', 0)}MHz ({s.get('manufacturer', 'Generic')})",
                    font=ctk.CTkFont(size=12),
                    text_color="#CBD5E1"
                )
                lbl.pack(anchor="w", padx=10, pady=2)

        # -------------------------------------------------------------
        # 5. STORAGE & SMART CARD
        # -------------------------------------------------------------
        self._clear_frame(self.card_storage.content)
        drives = storage.get("drives", [])
        if drives:
            d_box = ctk.CTkFrame(self.card_storage.content, fg_color="#0F172A", corner_radius=8)
            d_box.pack(fill="x", pady=2)
            d_box.grid_columnconfigure(0, weight=1)

            for idx, d in enumerate(drives):
                is_ok = d.get("is_smart_ok", True)
                status_color = "#10B981" if is_ok else "#EF4444"

                lbl_name = ctk.CTkLabel(
                    d_box,
                    text=f"• {d.get('model', 'Drive')} ({d.get('size_gb', 0)} GB)",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#F8FAFC"
                )
                lbl_name.grid(row=idx * 2, column=0, sticky="w", padx=12, pady=(6 if idx == 0 else 4, 1))

                lbl_sub = ctk.CTkLabel(
                    d_box,
                    text=f"   Type: {d.get('media_type', 'Storage')} | Bus: {d.get('interface', 'SATA/PCIe')} | S.M.A.R.T.: {d.get('smart_status', 'OK')}",
                    font=ctk.CTkFont(size=11),
                    text_color=status_color
                )
                lbl_sub.grid(row=idx * 2 + 1, column=0, sticky="w", padx=12, pady=(0, 6 if idx == len(drives) - 1 else 2))
        else:
            lbl = ctk.CTkLabel(self.card_storage.content, text="No physical drives detected", text_color="#94A3B8")
            lbl.pack(pady=10)

        # -------------------------------------------------------------
        # 6. GPU CARD
        # -------------------------------------------------------------
        self._clear_frame(self.card_gpu.content)
        adapters = gpu.get("adapters", [])
        if adapters:
            g_box = ctk.CTkFrame(self.card_gpu.content, fg_color="#0F172A", corner_radius=8)
            g_box.pack(fill="x", pady=2)
            g_box.grid_columnconfigure(0, weight=1)

            for idx, a in enumerate(adapters):
                is_ded = a.get("is_dedicated", False)
                type_badge = "Dedicated GPU" if is_ded else "Integrated Graphics"
                badge_color = "#38BDF8" if is_ded else "#94A3B8"

                lbl_gname = ctk.CTkLabel(
                    g_box,
                    text=f"• {a.get('name', 'GPU')} ({a.get('vram_gb', 0)} GB VRAM)",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="#F8FAFC"
                )
                lbl_gname.grid(row=idx * 2, column=0, sticky="w", padx=12, pady=(6 if idx == 0 else 4, 1))

                pnp_short = a.get("pnp_device_id", "N/A")
                if len(pnp_short) > 60:
                    pnp_short = pnp_short[:57] + "..."

                lbl_gsub = ctk.CTkLabel(
                    g_box,
                    text=f"   Type: {type_badge} | PNP: {pnp_short}",
                    font=ctk.CTkFont(size=11),
                    text_color=badge_color
                )
                lbl_gsub.grid(row=idx * 2 + 1, column=0, sticky="w", padx=12, pady=(0, 6 if idx == len(adapters) - 1 else 2))
        else:
            lbl = ctk.CTkLabel(self.card_gpu.content, text="No display adapters found", text_color="#94A3B8")
            lbl.pack(pady=10)

        # -------------------------------------------------------------
        # 7. CHASSIS & BIOS SERIAL CARD
        # -------------------------------------------------------------
        self._clear_frame(self.card_bios.content)
        bios_grid = ctk.CTkFrame(self.card_bios.content, fg_color="#0F172A", corner_radius=8)
        bios_grid.pack(fill="x", pady=2)
        bios_grid.grid_columnconfigure(1, weight=1)

        self._add_kv_row(bios_grid, 0, "Chassis Serial Number:", system.get("chassis_serial", "N/A"), is_code=True, color="#38BDF8")
        self._add_kv_row(bios_grid, 1, "Motherboard Model:", f"{system.get('motherboard_model', 'N/A')} (Serial: {system.get('motherboard_serial', 'N/A')})")
        self._add_kv_row(bios_grid, 2, "BIOS Version & Date:", f"{system.get('bios_version', 'N/A')} ({system.get('bios_date', 'N/A')[:8]})")
        self._add_kv_row(bios_grid, 3, "Hardware UUID:", system.get("uuid", "N/A"), is_code=True)

        lbl_chk = ctk.CTkLabel(
            self.card_bios.content,
            text="📌 BUYER VERIFICATION: Check the physical label / barcode sticker on the bottom of the laptop chassis.\n"
                 "If the printed serial does not match the BIOS Serial above, the motherboard has been replaced or chassis swapped.",
            font=ctk.CTkFont(size=11),
            text_color="#FDE047",
            justify="left"
        )
        lbl_chk.pack(anchor="w", padx=4, pady=(8, 2))

        # -------------------------------------------------------------
        # 8. BUYER ADVICE & NEGOTIATION POINTS
        # -------------------------------------------------------------
        self._clear_frame(self.card_advice.content)
        all_advice = []
        for rf in ev.get("red_flags", []):
            all_advice.append(("CRITICAL", rf, "#EF4444"))
        for w in ev.get("warnings", []):
            all_advice.append(("WARNING", w, "#F59E0B"))
        for s in ev.get("buyer_suggestions", []):
            all_advice.append(("ADVICE", s, "#38BDF8"))
        for g in ev.get("good_points", []):
            all_advice.append(("POSITIVE", g, "#10B981"))

        if all_advice:
            advice_box = ctk.CTkFrame(self.card_advice.content, fg_color="#0F172A", corner_radius=8)
            advice_box.pack(fill="x", pady=2)
            advice_box.grid_columnconfigure(1, weight=1)

            for idx, (tag, text, col) in enumerate(all_advice):
                tag_lbl = ctk.CTkLabel(
                    advice_box,
                    text=f"[{tag}]",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=col,
                    width=75
                )
                tag_lbl.grid(row=idx, column=0, padx=(10, 4), pady=(6 if idx == 0 else 3, 6 if idx == len(all_advice) - 1 else 3), sticky="nw")

                msg_lbl = ctk.CTkLabel(
                    advice_box,
                    text=text,
                    font=ctk.CTkFont(size=12),
                    text_color="#F8FAFC",
                    justify="left",
                    anchor="w"
                )
                msg_lbl.grid(row=idx, column=1, padx=(0, 12), pady=(6 if idx == 0 else 3, 6 if idx == len(all_advice) - 1 else 3), sticky="ew")
        else:
            lbl = ctk.CTkLabel(self.card_advice.content, text="No specific advice generated.", text_color="#94A3B8")
            lbl.pack(pady=10)

    def _add_kv_row(self, parent, row_idx, key, val, is_code=False, color="#F8FAFC", highlight=False):
        """Helper to add clean key-value rows in dark cards."""
        k_lbl = ctk.CTkLabel(
            parent,
            text=key,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94A3B8"
        )
        k_lbl.grid(row=row_idx, column=0, sticky="w", padx=12, pady=3)

        text_font = ctk.CTkFont(family="Consolas", size=11) if is_code else ctk.CTkFont(size=12)
        v_color = "#EF4444" if highlight else color

        v_lbl = ctk.CTkLabel(
            parent,
            text=str(val),
            font=text_font,
            text_color=v_color,
            justify="left",
            anchor="w"
        )
        v_lbl.grid(row=row_idx, column=1, sticky="ew", padx=12, pady=3)

    def _clear_frame(self, frame):
        """Cleans out existing widgets from a frame before repopulating."""
        for widget in frame.winfo_children():
            widget.destroy()

    def open_dead_pixel_tester(self):
        """Launches the interactive dead pixel & backlight bleed test tool."""
        launch_screen_test(parent=self)

    def export_reports(self):
        """Prompts user to select destination folder and exports HTML + TXT reports."""
        if not self.hardware_data:
            messagebox.showinfo("Wait", "System scan in progress. Please wait for completion.")
            return

        dest_dir = filedialog.askdirectory(title="Select Destination Directory for Inspection Reports (e.g. USB Drive)")
        if not dest_dir:
            return

        try:
            h_path, t_path = export_both_reports(
                self.hardware_data,
                self.battery_data,
                self.eval_data,
                output_dir=dest_dir
            )
            self.latest_html_report = h_path
            self.latest_txt_report = t_path
            self.btn_browser.configure(state="normal")

            ans = messagebox.askyesno(
                "Reports Saved Successfully",
                f"Inspection reports saved to:\n{h_path}\n\nWould you like to open the HTML report in your browser now?"
            )
            if ans:
                open_in_browser(h_path)
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export inspection reports:\n{e}")

    def view_in_browser(self):
        """Directly opens the latest generated HTML report in the default browser."""
        if self.latest_html_report and os.path.exists(self.latest_html_report):
            open_in_browser(self.latest_html_report)
        else:
            messagebox.showinfo("Report Not Ready", "Please re-scan the machine or export the report first.")


def _ensure_single_instance():
    """
    Ensures only a single instance of TrueSpec runs at any given time.
    If another instance is launched, activates the existing window and exits.
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        mutex_name = "Local\\TrueSpec_SecondHand_Inspector_SingleInstance_Mutex"
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            hwnd = ctypes.windll.user32.FindWindowW(None, "TrueSpec: Second-Hand Laptop Inspector v1.0")
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            sys.exit(0)
        return mutex
    except Exception:
        return None


def main():
    import multiprocessing
    multiprocessing.freeze_support()

    # Prevent cpuinfo from spawning subprocesses on Windows
    try:
        import cpuinfo
        cpuinfo.CAN_CALL_CPUID_IN_SUBPROCESS = False
        import cpuinfo.cpuinfo as c_internal
        c_internal.CAN_CALL_CPUID_IN_SUBPROCESS = False
    except Exception:
        pass

    # Ensure single instance
    mutex = _ensure_single_instance()

    # Force UTF-8 on Windows console if running with output attached
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    app = TrueSpecApp()
    app.mainloop()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
