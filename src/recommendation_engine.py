"""
TrueSpec: Second-Hand Laptop Inspector
Module: recommendation_engine.py
Author: TrueSpec Core Systems Team

Analyzes hardware & battery audit telemetry to produce:
1. Overall Laptop Health & Value Score (0–100)
2. Verdict Badge:
   - 🟢 SAFE TO BUY
   - 🟡 BUY WITH NEGOTIATION
   - 🔴 DO NOT BUY / HIGH RISK
3. Critical Red Flags & Warnings
4. Actionable Buyer Suggestions & Price Negotiation Arguments
"""

from typing import Dict, Any, List


def evaluate_laptop(hardware_data: Dict[str, Any], battery_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the laptop condition based on hardware audit and battery telemetry.
    Returns score (0-100), verdict badge, red flags, warnings, and buyer suggestions.
    """
    cpu = hardware_data.get("cpu", {})
    ram = hardware_data.get("ram", {})
    storage = hardware_data.get("storage", {})
    gpu = hardware_data.get("gpu", {})
    system = hardware_data.get("system", {})

    score = 100
    red_flags: List[str] = []
    warnings: List[str] = []
    good_points: List[str] = []
    buyer_suggestions: List[str] = []
    breakdown: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # 1. CPU INTEGRITY & ANTI-SPOOF CHECK
    # -------------------------------------------------------------
    if cpu.get("spoof_detected", False) or cpu.get("spoof_severity") == "CRITICAL":
        red_flags.append(
            f"FRAUDULENT REGISTRY SPOOF: The Registry reports '{cpu.get('registry_name')}' "
            f"but hardware CPUID silicon reports '{cpu.get('cpuid_name')}'!"
        )
        for reason in cpu.get("spoof_reasons", []):
            red_flags.append(f"• CPU Issue: {reason}")
        buyer_suggestions.append(
            "🚨 CRITICAL FRAUD DETECTED: Walk away immediately. The seller modified the Windows Registry "
            "to artificially inflate the CPU model/generation (e.g. disguise an i3 as an i7). Do not buy this machine."
        )
        # Immediate total failure
        score = 0
    else:
        good_points.append(
            f"Genuine Processor Verified: {cpu.get('cpuid_name', 'CPU')} "
            f"({cpu.get('physical_cores', 0)} Cores / {cpu.get('logical_threads', 0)} Threads)"
        )
        if cpu.get("spoof_severity") == "WARNING":
            for r in cpu.get("spoof_reasons", []):
                warnings.append(f"CPU Topology Notice: {r}")

    # -------------------------------------------------------------
    # 2. STORAGE HEALTH & S.M.A.R.T. STATUS
    # -------------------------------------------------------------
    if not storage.get("all_smart_ok", True):
        red_flags.append("S.M.A.R.T. STORAGE FAILURE: One or more storage drives report a failing or degraded health status.")
        buyer_suggestions.append(
            "🚨 DO NOT BUY: The internal drive has S.M.A.R.T. error warnings, meaning disk failure and total data loss are imminent. "
            "If you still wish to purchase, demand the seller replace the drive or deduct $50–$100 for an immediate replacement SSD."
        )
        score = min(score, 20)
    else:
        good_points.append("Storage S.M.A.R.T. Health status is OK (No drive failure predicted).")

    # SSD vs HDD Check
    if not storage.get("has_ssd", False) or not storage.get("primary_is_ssd", True):
        score -= 20
        warnings.append("System relies on a slow mechanical Hard Disk Drive (HDD) as the primary storage.")
        buyer_suggestions.append(
            "System lacks an SSD and will feel sluggish in daily use. Factor in the cost of an NVMe or SATA SSD upgrade ($30–$70) "
            "and use this as leverage to negotiate a lower price."
        )
        breakdown.append({"item": "Mechanical HDD Primary", "deduction": -20})
    else:
        good_points.append("Fast Solid State Drive (SSD/NVMe) installed as primary drive.")

    # -------------------------------------------------------------
    # 3. BATTERY HEALTH & WEAR ANALYSIS
    # -------------------------------------------------------------
    if battery_data.get("has_battery", False):
        health_pct = battery_data.get("health_percent", 0.0)
        cycles = battery_data.get("cycle_count", 0)

        if health_pct < 60.0:
            score -= 25
            warnings.append(
                f"Battery heavily degraded: {health_pct}% Health ({battery_data.get('wear_level_percent', 0)}% Wear)."
            )
            buyer_suggestions.append(
                "Battery is heavily degraded (<60% original capacity). Ask the seller for a price discount equal to a replacement battery ($40–$80), "
                "or request a new battery before purchase."
            )
            breakdown.append({"item": f"Severe Battery Wear ({health_pct}%)", "deduction": -25})
        elif health_pct < 80.0:
            score -= 10
            warnings.append(
                f"Moderate battery wear: {health_pct}% Health ({battery_data.get('wear_level_percent', 0)}% Wear)."
            )
            buyer_suggestions.append(
                "Moderate battery wear (60%–79%). Expect reduced unplugged runtime; negotiate a 5–10% discount off the asking price."
            )
            breakdown.append({"item": f"Moderate Battery Wear ({health_pct}%)", "deduction": -10})
        else:
            good_points.append(f"Healthy Battery: {health_pct}% remaining capacity.")

        # High cycle count warning
        if cycles > 500:
            score -= 5
            warnings.append(f"High battery cycle count ({cycles} charge cycles completed).")
            breakdown.append({"item": f"High Battery Cycles ({cycles})", "deduction": -5})
    else:
        # Desktop or removed battery
        warnings.append("No battery detected: The machine is running on AC wall power (Desktop PC, VM, or removed/missing laptop battery).")
        buyer_suggestions.append(
            "Verify whether a physical battery is present inside the laptop. If the battery was removed or is dead, budget for a replacement battery."
        )

    # -------------------------------------------------------------
    # 4. RAM ARCHITECTURE & CAPACITY
    # -------------------------------------------------------------
    total_ram = ram.get("total_gb", 0)
    slots_used = ram.get("slots_used", 0)
    slots_total = ram.get("slots_total", 0)
    channel_mode = ram.get("channel_mode", "Single-Channel")

    if total_ram < 8.0:
        score -= 15
        warnings.append(f"Low memory capacity: Only {total_ram} GB RAM installed.")
        free_slots = max(0, slots_total - slots_used)
        if free_slots > 0:
            buyer_suggestions.append(
                f"Laptop has low RAM ({total_ram} GB). Good news: {free_slots} free slot(s) available. "
                "Negotiate $20–$30 off to cover the cost of adding another 8GB RAM stick."
            )
        else:
            buyer_suggestions.append(
                f"Laptop has low RAM ({total_ram} GB) and all slots are occupied or soldered. "
                "Ensure this capacity is sufficient for your workload."
            )
        breakdown.append({"item": f"Low RAM Capacity ({total_ram}GB)", "deduction": -15})
    else:
        good_points.append(f"Adequate RAM capacity ({total_ram} GB installed).")

    if channel_mode == "Single-Channel" and total_ram >= 8.0:
        score -= 5
        free_slots = max(0, slots_total - slots_used)
        warnings.append(f"Single-Channel RAM mode active ({slots_used} of {slots_total} slots used).")
        if free_slots > 0:
            buyer_suggestions.append(
                "Memory is running in Single-Channel mode (1 slot populated). Adding a second RAM stick will double memory bandwidth "
                "and significantly boost integrated GPU and multitasking performance."
            )
        breakdown.append({"item": "Single-Channel Memory Mode", "deduction": -5})
    elif channel_mode == "Dual-Channel":
        good_points.append(f"Dual-Channel RAM active ({slots_used} of {slots_total} slots used) - optimal memory bandwidth.")

    # -------------------------------------------------------------
    # 5. CHASSIS SERIAL & MOTHERBOARD INTEGRITY
    # -------------------------------------------------------------
    chassis_serial = system.get("chassis_serial", "")
    if system.get("suspicious_serial", False):
        score -= 5
        warnings.append(f"Generic / Placeholder Chassis Serial: '{chassis_serial}'.")
        buyer_suggestions.append(
            "The BIOS/chassis serial contains a generic string (e.g. 'Default string' or 'To be filled by OEM'). "
            "This suggests the motherboard was replaced, flashed with generic firmware, or refurbished. "
            "Carefully cross-check the physical serial number label on the bottom case cover."
        )
        breakdown.append({"item": "Generic BIOS Serial String", "deduction": -5})
    else:
        if chassis_serial and chassis_serial != "Unknown":
            buyer_suggestions.append(
                f"Physical Inspection Tip: Check the bottom chassis sticker or under the battery to verify the serial matches "
                f"the reported BIOS serial: '{chassis_serial}'."
            )

    # -------------------------------------------------------------
    # 6. DEDICATED GPU (BONUS VALUE)
    # -------------------------------------------------------------
    if gpu.get("has_dedicated_gpu", False):
        good_points.append(f"Dedicated Discrete Graphics Card detected ({gpu.get('summary_text')}).")

    # Clamping score between 0 and 100
    score = max(0, min(100, score))

    # -------------------------------------------------------------
    # FINAL VERDICT BADGE ASSIGNMENT
    # -------------------------------------------------------------
    if red_flags:
        verdict_badge = "🔴 DO NOT BUY / HIGH RISK"
        verdict_level = "REJECT"
        if cpu.get("spoof_detected", False):
            verdict_title = "DO NOT BUY: Fraudulent Registry Modification Detected"
        else:
            verdict_title = "DO NOT BUY: Critical Hardware Defect Detected"
    elif score >= 80:
        verdict_badge = "🟢 SAFE TO BUY"
        verdict_level = "SAFE"
        verdict_title = "Hardware passed inspection in healthy working condition"
        if not buyer_suggestions:
            buyer_suggestions.append("Hardware is in great condition. Standard physical inspection of hinges, screen, and keyboard recommended.")
    elif score >= 55:
        verdict_badge = "🟡 BUY WITH NEGOTIATION"
        verdict_level = "NEGOTIATE"
        verdict_title = "Acceptable machine with wear or bottlenecks – negotiate price discount"
    else:
        verdict_badge = "🔴 DO NOT BUY / HIGH RISK"
        verdict_level = "REJECT"
        verdict_title = "High wear or multiple hardware bottlenecks detected"

    return {
        "score": score,
        "verdict_badge": verdict_badge,
        "verdict_level": verdict_level,
        "verdict_title": verdict_title,
        "red_flags": red_flags,
        "warnings": warnings,
        "good_points": good_points,
        "buyer_suggestions": buyer_suggestions,
        "breakdown": breakdown
    }


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    from hardware_audit import get_full_hardware_audit
    from battery_audit import get_battery_audit
    import pprint

    print("--- Running Recommendation Engine Test ---")
    hw = get_full_hardware_audit()
    bat = get_battery_audit()
    eval_result = evaluate_laptop(hw, bat)
    pprint.pprint(eval_result)
