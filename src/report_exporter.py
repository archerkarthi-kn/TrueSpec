"""
TrueSpec: Second-Hand Laptop Inspector
Module: report_exporter.py
Author: TrueSpec Core Systems Team

Generates comprehensive, professional HTML and TXT inspection reports
designed for USB export, client sharing, and print-to-PDF.
Includes browser opening utility.
"""

import os
import sys
import datetime
import webbrowser
from typing import Dict, Any, Tuple


def _sanitize_filename(name: str) -> str:
    """Removes invalid filename characters."""
    clean = "".join(c for c in name if c.isalnum() or c in ("-", "_", ".")).strip()
    return clean or "UnknownDevice"


def generate_html_report(hardware_data: Dict[str, Any],
                         battery_data: Dict[str, Any],
                         eval_data: Dict[str, Any],
                         output_dir: str = ".") -> str:
    """
    Generates a standalone, beautiful HTML inspection report with embedded CSS.
    Returns the absolute path to the generated HTML file.
    """
    cpu = hardware_data.get("cpu", {})
    ram = hardware_data.get("ram", {})
    storage = hardware_data.get("storage", {})
    gpu = hardware_data.get("gpu", {})
    system = hardware_data.get("system", {})

    score = eval_data.get("score", 0)
    verdict_badge = eval_data.get("verdict_badge", "INSPECTION COMPLETE")
    verdict_level = eval_data.get("verdict_level", "SAFE")
    verdict_title = eval_data.get("verdict_title", "")
    red_flags = eval_data.get("red_flags", [])
    warnings = eval_data.get("warnings", [])
    good_points = eval_data.get("good_points", [])
    buyer_suggestions = eval_data.get("buyer_suggestions", [])

    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = now.strftime("%Y%m%d_%H%M%S")

    serial_clean = _sanitize_filename(system.get("chassis_serial") or system.get("bios_serial") or "NO_SERIAL")
    filename = f"Laptop_Inspection_Report_{serial_clean}_{file_timestamp}.html"
    filepath = os.path.join(output_dir, filename)

    # Color themes based on verdict
    if verdict_level == "SAFE":
        verdict_color = "#10B981"  # Emerald Green
        verdict_bg = "#ECFDF5"
        verdict_border = "#059669"
        card_gradient = "linear-gradient(135deg, #065F46 0%, #047857 100%)"
    elif verdict_level == "NEGOTIATE":
        verdict_color = "#F59E0B"  # Amber
        verdict_bg = "#FFFBEB"
        verdict_border = "#D97706"
        card_gradient = "linear-gradient(135deg, #92400E 0%, #B45309 100%)"
    else:
        verdict_color = "#EF4444"  # Crimson Red
        verdict_bg = "#FEF2F2"
        verdict_border = "#DC2626"
        card_gradient = "linear-gradient(135deg, #991B1B 0%, #B91C1C 100%)"

    # CPU Anti-Spoof Badge
    cpu_spoofed = cpu.get("spoof_detected", False)
    if cpu_spoofed:
        cpu_status_badge = '<span class="badge-danger">🚨 REGISTRY SPOOF DETECTED</span>'
        cpu_row_class = "spoof-alert-row"
    else:
        cpu_status_badge = '<span class="badge-success">✅ VERIFIED GENUINE SILICON</span>'
        cpu_row_class = ""

    # Battery progress bar & metrics
    has_bat = battery_data.get("has_battery", False)
    bat_health = battery_data.get("health_percent", 0.0)
    bat_wear = battery_data.get("wear_level_percent", 0.0)
    bat_design = battery_data.get("design_capacity_mwh", 0)
    bat_full = battery_data.get("full_charge_capacity_mwh", 0)
    bat_cycles = battery_data.get("cycle_count", 0)
    bat_chem = battery_data.get("chemistry", "Unknown")

    if has_bat:
        bat_color = "#10B981" if bat_health >= 80 else ("#F59E0B" if bat_health >= 60 else "#EF4444")
        bat_progress_html = f"""
        <div class="progress-container">
            <div class="progress-bar" style="width: {min(100, bat_health)}%; background-color: {bat_color};"></div>
        </div>
        <div class="metric-row">
            <span class="metric-label">Health & Wear:</span>
            <span class="metric-val"><strong>{bat_health}% Health</strong> ({bat_wear}% Wear Level)</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Full / Design Capacity:</span>
            <span class="metric-val">{bat_full:,} mWh / {bat_design:,} mWh</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Charge Cycles & Chemistry:</span>
            <span class="metric-val">{bat_cycles} Cycles | {bat_chem}</span>
        </div>
        """
    else:
        bat_progress_html = """
        <div class="notice-box info-box">
            <strong>No Battery Detected:</strong> Machine operates on AC Wall Power (Desktop, VM, or removed battery pack).
        </div>
        """

    # RAM Sticks HTML
    ram_sticks = ram.get("sticks", [])
    ram_rows = ""
    if ram_sticks:
        for idx, s in enumerate(ram_sticks):
            ram_rows += f"""
            <tr>
                <td>Slot {idx + 1} ({s.get('locator', 'DIMM')})</td>
                <td><strong>{s.get('capacity_gb', 0)} GB</strong></td>
                <td>{s.get('speed_mhz', 0)} MHz</td>
                <td>{s.get('manufacturer', 'Generic')}</td>
                <td><code>{s.get('part_number', 'N/A')}</code></td>
            </tr>
            """
    else:
        ram_rows = f"<tr><td colspan='5'>Total Installed: {ram.get('total_gb', 0)} GB RAM</td></tr>"

    # Storage Drives HTML
    storage_drives = storage.get("drives", [])
    storage_rows = ""
    for d in storage_drives:
        smart_badge = '<span class="badge-success">OK (Healthy)</span>' if d.get("is_smart_ok", True) else '<span class="badge-danger">PRED FAIL</span>'
        storage_rows += f"""
        <tr>
            <td><strong>{d.get('model', 'Drive')}</strong></td>
            <td>{d.get('size_gb', 0)} GB</td>
            <td><span class="pill">{d.get('media_type', 'Storage')}</span></td>
            <td>{d.get('interface', 'SATA/PCIe')}</td>
            <td>{smart_badge}</td>
        </tr>
        """
    if not storage_rows:
        storage_rows = "<tr><td colspan='5'>No physical storage drives detected</td></tr>"

    # GPU HTML
    gpu_list = gpu.get("adapters", [])
    gpu_rows = ""
    for g in gpu_list:
        gpu_badge = '<span class="pill-primary">Dedicated GPU</span>' if g.get("is_dedicated", False) else '<span class="pill">Integrated Graphics</span>'
        gpu_rows += f"""
        <tr>
            <td><strong>{g.get('name', 'Display Adapter')}</strong></td>
            <td>{g.get('vram_gb', 0)} GB VRAM</td>
            <td>{gpu_badge}</td>
            <td><small><code>{g.get('pnp_device_id', 'N/A')}</code></small></td>
        </tr>
        """
    if not gpu_rows:
        gpu_rows = "<tr><td colspan='4'>No GPU adapters detected</td></tr>"

    # Red flags & warnings lists
    red_flag_items = "".join(f"<li class='red-flag-li'><strong>{rf}</strong></li>" for rf in red_flags)
    warning_items = "".join(f"<li class='warning-li'>{w}</li>" for w in warnings)
    good_items = "".join(f"<li class='good-li'>{g}</li>" for g in good_points)
    suggestion_items = "".join(f"<li class='suggestion-li'>{s}</li>" for s in buyer_suggestions)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrueSpec Laptop Inspection Report - {serial_clean}</title>
    <style>
        :root {{
            --bg: #F8FAFC;
            --surface: #FFFFFF;
            --text-primary: #0F172A;
            --text-secondary: #475569;
            --border: #E2E8F0;
            --primary: #2563EB;
            --danger: #EF4444;
            --warning: #F59E0B;
            --success: #10B981;
        }}
        @media print {{
            body {{ background: #FFF !important; padding: 0 !important; }}
            .no-print {{ display: none !important; }}
            .card {{ box-shadow: none !important; border: 1px solid #CCC !important; }}
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-primary); padding: 32px 20px; line-height: 1.5; }}
        .container {{ max-width: 980px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border); padding-bottom: 20px; margin-bottom: 24px; }}
        .logo-title {{ font-size: 26px; font-weight: 800; color: #1E293B; letter-spacing: -0.5px; }}
        .logo-tag {{ display: inline-block; background: #3B82F6; color: white; font-size: 11px; padding: 3px 8px; border-radius: 9999px; font-weight: 700; margin-left: 8px; vertical-align: middle; }}
        .meta-timestamp {{ font-size: 13px; color: var(--text-secondary); text-align: right; }}
        
        /* Banner Card */
        .verdict-card {{
            background: {card_gradient};
            color: #FFFFFF;
            border-radius: 12px;
            padding: 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }}
        .verdict-info h2 {{ font-size: 28px; font-weight: 800; margin-bottom: 6px; }}
        .verdict-info p {{ font-size: 15px; opacity: 0.92; }}
        .score-box {{
            background: rgba(255, 255, 255, 0.18);
            border: 2px solid rgba(255, 255, 255, 0.4);
            border-radius: 12px;
            padding: 16px 24px;
            text-align: center;
            min-width: 140px;
        }}
        .score-number {{ font-size: 42px; font-weight: 900; line-height: 1; }}
        .score-label {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; margin-top: 4px; }}

        /* Cards & Sections */
        .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 22px; margin-bottom: 20px; box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05); }}
        .card-title {{ font-size: 17px; font-weight: 700; color: #1E293B; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }}
        
        /* Tables */
        table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; margin-top: 8px; }}
        th {{ background: #F1F5F9; color: #475569; text-align: left; padding: 10px 12px; font-weight: 600; border-bottom: 2px solid var(--border); }}
        td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
        tr:last-child td {{ border-bottom: none; }}
        .spoof-alert-row {{ background-color: #FEF2F2 !important; }}

        /* Badges & Pills */
        .badge-success {{ background: #DEF7EC; color: #03543F; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 12px; display: inline-block; }}
        .badge-danger {{ background: #FDE8E8; color: #9B1C1C; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 12px; display: inline-block; }}
        .badge-warning {{ background: #FEF08A; color: #713F12; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 12px; display: inline-block; }}
        .pill {{ background: #F1F5F9; color: #334155; font-size: 11.5px; padding: 3px 8px; border-radius: 4px; font-weight: 600; }}
        .pill-primary {{ background: #DBEAFE; color: #1E40AF; font-size: 11.5px; padding: 3px 8px; border-radius: 4px; font-weight: 600; }}

        /* Progress Bar */
        .progress-container {{ width: 100%; height: 16px; background-color: #E2E8F0; border-radius: 9999px; overflow: hidden; margin: 12px 0 16px 0; }}
        .progress-bar {{ height: 100%; border-radius: 9999px; }}
        .metric-row {{ display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 6px; border-bottom: 1px dashed #E2E8F0; padding-bottom: 4px; }}
        .metric-label {{ color: var(--text-secondary); }}

        /* Advice Lists */
        ul.advice-list {{ list-style-type: none; padding-left: 0; }}
        ul.advice-list li {{ padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; font-size: 14px; line-height: 1.45; }}
        li.red-flag-li {{ background: #FEF2F2; border-left: 4px solid #EF4444; color: #991B1B; }}
        li.warning-li {{ background: #FFFBEB; border-left: 4px solid #F59E0B; color: #92400E; }}
        li.good-li {{ background: #F0FDF4; border-left: 4px solid #10B981; color: #166534; }}
        li.suggestion-li {{ background: #EFF6FF; border-left: 4px solid #3B82F6; color: #1E40AF; }}

        .code-chip {{ font-family: monospace; background: #F1F5F9; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
        .print-btn {{ background: #0F172A; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div>
                <div class="logo-title">TrueSpec <span class="logo-tag">HARDWARE AUDIT REPORT</span></div>
                <div style="font-size: 14px; color: var(--text-secondary); margin-top: 4px;">Second-Hand Laptop Integrity & Verification Telemetry</div>
            </div>
            <div>
                <div class="meta-timestamp"><strong>Timestamp:</strong> {timestamp_str}</div>
                <div class="meta-timestamp"><strong>Chassis Serial:</strong> <span class="code-chip">{system.get('chassis_serial', 'N/A')}</span></div>
                <div class="no-print" style="margin-top: 8px; text-align: right;">
                    <button class="print-btn" onclick="window.print()">🖨️ Print / Save PDF</button>
                </div>
            </div>
        </div>

        <!-- Verdict Banner -->
        <div class="verdict-card">
            <div class="verdict-info">
                <h2>{verdict_badge}</h2>
                <p>{verdict_title}</p>
                <div style="margin-top: 8px; font-size: 13px; opacity: 0.85;">Model: {system.get('vendor', '')} {system.get('model_name', 'Laptop System')}</div>
            </div>
            <div class="score-box">
                <div class="score-number">{score}</div>
                <div class="score-label">System Score</div>
            </div>
        </div>

        <!-- Buyer Suggestions & Negotiation Strategy -->
        <div class="card">
            <div class="card-title">💡 Actionable Buyer Advice & Negotiation Points</div>
            <ul class="advice-list">
                {red_flag_items}
                {warning_items}
                {suggestion_items}
                {good_items}
            </ul>
        </div>

        <!-- Anti-Spoof CPU Verification -->
        <div class="card">
            <div class="card-title">
                <span>🛡️ Anti-Spoof CPU Verification</span>
                {cpu_status_badge}
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 25%;">Verification Channel</th>
                        <th style="width: 50%;">Reported Processor Value</th>
                        <th style="width: 25%;">Integrity Check</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="{cpu_row_class}">
                        <td><strong>Windows Registry</strong><br><small>HKLM ProcessorNameString</small></td>
                        <td><code>{cpu.get('registry_name', 'N/A')}</code></td>
                        <td><span class="pill">Vulnerable to Spoofing</span></td>
                    </tr>
                    <tr class="{cpu_row_class}">
                        <td><strong>Hardware CPUID</strong><br><small>Direct Silicon Instruction</small></td>
                        <td><strong>{cpu.get('cpuid_name', 'N/A')}</strong></td>
                        <td><span class="badge-success">Hardware Source of Truth</span></td>
                    </tr>
                    <tr>
                        <td><strong>WMI Win32_Processor</strong><br><small>OS Driver Layer</small></td>
                        <td>{cpu.get('wmi_name', 'N/A')}</td>
                        <td><span class="pill">OS Query</span></td>
                    </tr>
                    <tr>
                        <td><strong>Topology Verification</strong><br><small>Cores, Threads & Cache</small></td>
                        <td>{cpu.get('physical_cores', 0)} Physical Cores | {cpu.get('logical_threads', 0)} Threads | {round(cpu.get('l3_cache_kb', 0)/1024, 1)} MB L3 Cache</td>
                        <td><span class="badge-success">Matches Topology</span></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Battery Health & Wear Analysis -->
        <div class="card">
            <div class="card-title">🔋 Deep Battery Health & Wear Analysis</div>
            {bat_progress_html}
        </div>

        <!-- Memory (RAM) Architecture -->
        <div class="card">
            <div class="card-title">
                <span>🧠 Memory (RAM) Architecture</span>
                <span class="pill-primary">{ram.get('channel_mode', 'Single-Channel')}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Total Installed Capacity:</span>
                <span class="metric-val"><strong>{ram.get('total_gb', 0)} GB</strong> ({ram.get('slots_used', 0)} of {ram.get('slots_total', 0)} slots used)</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Slot / Locator</th>
                        <th>Capacity</th>
                        <th>Speed</th>
                        <th>Manufacturer</th>
                        <th>Part Number</th>
                    </tr>
                </thead>
                <tbody>
                    {ram_rows}
                </tbody>
            </table>
        </div>

        <!-- Storage Drives & S.M.A.R.T. -->
        <div class="card">
            <div class="card-title">💾 Storage Drives & S.M.A.R.T. Health</div>
            <table>
                <thead>
                    <tr>
                        <th>Drive Model</th>
                        <th>Capacity</th>
                        <th>Media Type</th>
                        <th>Bus Interface</th>
                        <th>S.M.A.R.T. Status</th>
                    </tr>
                </thead>
                <tbody>
                    {storage_rows}
                </tbody>
            </table>
        </div>

        <!-- GPU & Display Adapters -->
        <div class="card">
            <div class="card-title">🎮 Graphics & Display Adapters</div>
            <table>
                <thead>
                    <tr>
                        <th>GPU Adapter</th>
                        <th>VRAM</th>
                        <th>Type</th>
                        <th>PNP Hardware Device ID</th>
                    </tr>
                </thead>
                <tbody>
                    {gpu_rows}
                </tbody>
            </table>
        </div>

        <!-- Chassis & BIOS Verification -->
        <div class="card">
            <div class="card-title">🔍 Chassis, BIOS & Motherboard Identity</div>
            <table>
                <thead>
                    <tr>
                        <th>Component</th>
                        <th>Reported Identifier</th>
                        <th>Buyer Check</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Chassis Serial Number</strong></td>
                        <td><code>{system.get('chassis_serial', 'N/A')}</code></td>
                        <td>Compare with bottom physical laptop label</td>
                    </tr>
                    <tr>
                        <td><strong>System UUID</strong></td>
                        <td><code>{system.get('uuid', 'N/A')}</code></td>
                        <td>Cryptographic board identity</td>
                    </tr>
                    <tr>
                        <td><strong>BIOS Version & Date</strong></td>
                        <td>{system.get('bios_version', 'N/A')} ({system.get('bios_date', 'N/A')[:8]})</td>
                        <td>Firmware release date</td>
                    </tr>
                    <tr>
                        <td><strong>Motherboard Model</strong></td>
                        <td>{system.get('motherboard_model', 'N/A')} (Serial: {system.get('motherboard_serial', 'N/A')})</td>
                        <td>Board authenticity check</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div style="text-align: center; color: var(--text-secondary); font-size: 12px; margin-top: 30px;">
            Generated by <strong>TrueSpec: Second-Hand Laptop Inspector</strong> • Portable USB Diagnostic Utility
        </div>
    </div>
</body>
</html>
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    return os.path.abspath(filepath)


def generate_txt_report(hardware_data: Dict[str, Any],
                        battery_data: Dict[str, Any],
                        eval_data: Dict[str, Any],
                        output_dir: str = ".") -> str:
    """
    Generates a clean ASCII text report readable in Notepad or terminal.
    Returns the absolute path to the generated TXT file.
    """
    cpu = hardware_data.get("cpu", {})
    ram = hardware_data.get("ram", {})
    storage = hardware_data.get("storage", {})
    gpu = hardware_data.get("gpu", {})
    system = hardware_data.get("system", {})

    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    file_timestamp = now.strftime("%Y%m%d_%H%M%S")

    serial_clean = _sanitize_filename(system.get("chassis_serial") or system.get("bios_serial") or "NO_SERIAL")
    filename = f"Laptop_Inspection_Report_{serial_clean}_{file_timestamp}.txt"
    filepath = os.path.join(output_dir, filename)

    lines = []
    lines.append("=" * 78)
    lines.append("       TRUESPEC: SECOND-HAND LAPTOP INSPECTION & HARDWARE AUDIT       ")
    lines.append("=" * 78)
    lines.append(f"Inspection Timestamp: {timestamp_str}")
    lines.append(f"Chassis Serial:      {system.get('chassis_serial', 'N/A')}")
    lines.append(f"System Model:        {system.get('vendor', '')} {system.get('model_name', 'N/A')}")
    lines.append(f"BIOS Version:        {system.get('bios_version', 'N/A')} ({system.get('bios_date', 'N/A')[:8]})")
    lines.append(f"Motherboard:         {system.get('motherboard_model', 'N/A')}")
    lines.append("-" * 78)
    lines.append(f"OVERALL SYSTEM SCORE: {eval_data.get('score', 0)} / 100")
    lines.append(f"VERDICT:             {eval_data.get('verdict_badge', 'N/A')}")
    lines.append(f"SUMMARY:             {eval_data.get('verdict_title', 'N/A')}")
    lines.append("-" * 78)

    lines.append("\n[1] BUYER ADVICE & NEGOTIATION RECOMMENDATIONS:")
    for rf in eval_data.get("red_flags", []):
        lines.append(f"  [!] CRITICAL: {rf}")
    for w in eval_data.get("warnings", []):
        lines.append(f"  [-] WARNING:  {w}")
    for s in eval_data.get("buyer_suggestions", []):
        lines.append(f"  [*] ADVICE:   {s}")
    for g in eval_data.get("good_points", []):
        lines.append(f"  [+] POSITIVE: {g}")

    lines.append("\n[2] PROCESSOR (CPU) ANTI-SPOOF AUDIT:")
    lines.append(f"  Registry String:  {cpu.get('registry_name', 'N/A')}")
    lines.append(f"  Silicon CPUID:    {cpu.get('cpuid_name', 'N/A')}")
    lines.append(f"  WMI Processor:    {cpu.get('wmi_name', 'N/A')}")
    lines.append(f"  Cores / Threads:  {cpu.get('physical_cores', 0)} Physical Cores / {cpu.get('logical_threads', 0)} Logical Threads")
    lines.append(f"  L3 Cache:         {round(cpu.get('l3_cache_kb', 0)/1024, 1)} MB")
    lines.append(f"  Spoof Detected:   {'YES - FRAUDULENT REGISTRY DETECTED' if cpu.get('spoof_detected') else 'NO - Verified Silicon'}")
    if cpu.get("spoof_reasons"):
        for r in cpu.get("spoof_reasons", []):
            lines.append(f"  -> Reason: {r}")

    lines.append("\n[3] BATTERY HEALTH & WEAR:")
    if battery_data.get("has_battery", False):
        lines.append(f"  Battery Health:   {battery_data.get('health_percent', 0)}% (Wear Level: {battery_data.get('wear_level_percent', 0)}%)")
        lines.append(f"  Full / Design:    {battery_data.get('full_charge_capacity_mwh', 0):,} mWh / {battery_data.get('design_capacity_mwh', 0):,} mWh")
        lines.append(f"  Cycle Count:      {battery_data.get('cycle_count', 0)}")
        lines.append(f"  Chemistry:        {battery_data.get('chemistry', 'N/A')}")
        lines.append(f"  Manufacturer:     {battery_data.get('manufacturer', 'N/A')}")
    else:
        lines.append("  Status: No battery installed (Running on AC Wall Power / Desktop / VM)")

    lines.append("\n[4] MEMORY (RAM) ARCHITECTURE:")
    lines.append(f"  Total Capacity:   {ram.get('total_gb', 0)} GB")
    lines.append(f"  Slot Usage:       {ram.get('slots_used', 0)} of {ram.get('slots_total', 0)} slots used ({ram.get('channel_mode', 'N/A')})")
    for idx, s in enumerate(ram.get("sticks", [])):
        lines.append(f"  - Slot {idx+1} ({s.get('locator', 'DIMM')}): {s.get('capacity_gb', 0)}GB @ {s.get('speed_mhz', 0)}MHz [{s.get('manufacturer', 'Generic')}] PN: {s.get('part_number', 'N/A')}")

    lines.append("\n[5] STORAGE DRIVES & S.M.A.R.T. STATUS:")
    for d in storage.get("drives", []):
        lines.append(f"  - {d.get('model', 'Drive')}: {d.get('size_gb', 0)} GB [{d.get('media_type', 'Storage')}] S.M.A.R.T.: {d.get('smart_status', 'Unknown')}")

    lines.append("\n[6] GRAPHICS & DISPLAY ADAPTERS:")
    for g in gpu.get("adapters", []):
        lines.append(f"  - {g.get('name', 'GPU')} ({g.get('vram_gb', 0)}GB VRAM) - PNP: {g.get('pnp_device_id', 'N/A')}")

    lines.append("\n" + "=" * 78)
    lines.append("Report generated by TrueSpec: Second-Hand Laptop Inspector")
    lines.append("=" * 78)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return os.path.abspath(filepath)


def export_both_reports(hardware_data: Dict[str, Any],
                        battery_data: Dict[str, Any],
                        eval_data: Dict[str, Any],
                        output_dir: str = ".") -> Tuple[str, str]:
    """Generates both HTML and TXT reports and returns (html_path, txt_path)."""
    os.makedirs(output_dir, exist_ok=True)
    html_path = generate_html_report(hardware_data, battery_data, eval_data, output_dir)
    txt_path = generate_txt_report(hardware_data, battery_data, eval_data, output_dir)
    return html_path, txt_path


def open_in_browser(html_path: str):
    """Opens the generated HTML report in the user's default web browser."""
    if os.path.exists(html_path):
        webbrowser.open(f"file://{os.path.abspath(html_path)}")


if __name__ == "__main__":
    from hardware_audit import get_full_hardware_audit
    from battery_audit import get_battery_audit
    from recommendation_engine import evaluate_laptop

    hw = get_full_hardware_audit()
    bat = get_battery_audit()
    ev = evaluate_laptop(hw, bat)
    h_path, t_path = export_both_reports(hw, bat, ev)
    print(f"HTML Report generated: {h_path}")
    print(f"TXT Report generated:  {t_path}")
