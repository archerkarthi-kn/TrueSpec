"""
TrueSpec: Second-Hand Laptop Inspector
Module: battery_audit.py
Author: TrueSpec Core Systems Team

Automates execution of `powercfg /batteryreport /xml` and parses hardware
capacity, health percentage, wear level, chemistry, and cycle count.
Handles desktop/VM environments (no battery) gracefully.
"""

import os
import sys
import uuid
import tempfile
import subprocess
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
import psutil


def _strip_ns(tag: str) -> str:
    """Strips XML namespace from tag if present."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def get_battery_audit() -> Dict[str, Any]:
    """
    Executes Windows powercfg battery report silently, parses XML output,
    and returns comprehensive battery health metrics.
    Guarantees temporary file cleanup.
    """
    result: Dict[str, Any] = {
        "has_battery": False,
        "batteries_count": 0,
        "design_capacity_mwh": 0,
        "full_charge_capacity_mwh": 0,
        "health_percent": 0.0,
        "wear_level_percent": 0.0,
        "cycle_count": 0,
        "chemistry": "Unknown",
        "manufacturer": "Unknown",
        "serial_number": "Unknown",
        "battery_id": "Unknown",
        "is_plugged": False,
        "current_charge_percent": 0,
        "status_level": "INFO",  # GOOD, MODERATE, CRITICAL, NO_BATTERY
        "summary_text": "No battery detected",
        "batteries_list": []
    }

    # 1. Quick check with psutil
    ps_bat = None
    try:
        ps_bat = psutil.sensors_battery()
        if ps_bat:
            result["is_plugged"] = bool(ps_bat.power_plugged)
            result["current_charge_percent"] = round(ps_bat.percent, 1)
    except Exception as e:
        print(f"[BatteryAudit] psutil battery read warning: {e}", file=sys.stderr)

    # 2. Silently generate powercfg battery report XML
    temp_dir = tempfile.gettempdir()
    unique_filename = f"truespec_bat_{uuid.uuid4().hex[:8]}.xml"
    xml_path = os.path.join(temp_dir, unique_filename)

    try:
        # Run powercfg command with CREATE_NO_WINDOW
        cmd = ["powercfg", "/batteryreport", "/xml", "/output", xml_path]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )

        if not os.path.exists(xml_path):
            if not ps_bat:
                result["summary_text"] = "No battery installed (Desktop PC / VM / Removed)"
                result["status_level"] = "NO_BATTERY"
                return result
            else:
                result["has_battery"] = True
                result["summary_text"] = f"Battery Present ({result['current_charge_percent']}%, { 'Plugged' if result['is_plugged'] else 'Unplugged'})"
                result["status_level"] = "INFO"
                return result

        # 3. Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Find Batteries container (handling arbitrary namespace)
        batteries_el = None
        for child in root:
            if _strip_ns(child.tag) == "Batteries":
                batteries_el = child
                break

        found_batteries = []
        if batteries_el is not None:
            for b in batteries_el:
                if _strip_ns(b.tag) == "Battery":
                    bat_dict = {}
                    for field in b:
                        tag_name = _strip_ns(field.tag)
                        bat_dict[tag_name] = field.text.strip() if field.text else ""
                    found_batteries.append(bat_dict)

        # In case Batteries section was empty, check History entries for latest recorded capacities
        if not found_batteries:
            history_el = None
            for child in root:
                if _strip_ns(child.tag) == "History":
                    history_el = child
                    break
            if history_el is not None:
                # Walk in reverse to find last non-zero entry
                for entry in reversed(list(history_el)):
                    des = int(entry.attrib.get("DesignCapacity", 0) or 0)
                    full = int(entry.attrib.get("FullChargeCapacity", 0) or 0)
                    if des > 0 and full > 0:
                        found_batteries.append({
                            "DesignCapacity": str(des),
                            "FullChargeCapacity": str(full),
                            "CycleCount": str(entry.attrib.get("CycleCount", 0)),
                            "Manufacturer": "Historical Record",
                            "Chemistry": "Lithium"
                        })
                        break

        if not found_batteries:
            result["has_battery"] = False
            result["summary_text"] = "No battery installed (Desktop PC / VM / Removed)"
            result["status_level"] = "NO_BATTERY"
            return result

        # Extract primary / aggregated battery data
        total_design = 0
        total_full = 0
        max_cycles = 0

        for bat in found_batteries:
            des = int(bat.get("DesignCapacity", 0) or 0)
            full = int(bat.get("FullChargeCapacity", 0) or 0)
            cycles_raw = bat.get("CycleCount", 0)
            try:
                cycles = int(cycles_raw or 0)
            except ValueError:
                cycles = 0

            total_design += des
            total_full += full
            if cycles > max_cycles:
                max_cycles = cycles

            individual_health = round((full / des) * 100, 1) if des > 0 else 0.0
            result["batteries_list"].append({
                "id": bat.get("Id", "BAT0"),
                "manufacturer": bat.get("Manufacturer", "Unknown"),
                "serial_number": bat.get("SerialNumber", "Unknown"),
                "chemistry": bat.get("Chemistry", "Unknown"),
                "design_capacity_mwh": des,
                "full_charge_capacity_mwh": full,
                "cycle_count": cycles,
                "health_percent": individual_health
            })

        result["has_battery"] = True
        result["batteries_count"] = len(found_batteries)
        result["design_capacity_mwh"] = total_design
        result["full_charge_capacity_mwh"] = total_full
        result["cycle_count"] = max_cycles

        # Primary battery meta
        primary = found_batteries[0]
        result["manufacturer"] = primary.get("Manufacturer", "Unknown")
        result["chemistry"] = primary.get("Chemistry", "Unknown")
        result["serial_number"] = primary.get("SerialNumber", "Unknown")
        result["battery_id"] = primary.get("Id", "Unknown")

        # Health & Wear calculation
        if total_design > 0:
            health = round((total_full / total_design) * 100.0, 1)
            # Cap health at 100% for display wear calculation, though some new batteries have >100%
            result["health_percent"] = health
            result["wear_level_percent"] = round(max(0.0, 100.0 - health), 1)

            if health >= 80.0:
                result["status_level"] = "GOOD"
            elif health >= 60.0:
                result["status_level"] = "MODERATE"
            else:
                result["status_level"] = "CRITICAL"

            plugged_str = "Plugged In" if result["is_plugged"] else "On Battery"
            result["summary_text"] = (
                f"{health}% Health (Wear: {result['wear_level_percent']}%) | "
                f"{total_full:,} / {total_design:,} mWh | {max_cycles} Cycles ({plugged_str})"
            )
        else:
            result["health_percent"] = 0.0
            result["wear_level_percent"] = 0.0
            result["summary_text"] = "Battery present but capacity values not reported by ACPI"
            result["status_level"] = "MODERATE"

    except Exception as e:
        print(f"[BatteryAudit] Error running/parsing battery report: {e}", file=sys.stderr)
        if ps_bat:
            result["has_battery"] = True
            result["current_charge_percent"] = round(ps_bat.percent, 1)
            result["is_plugged"] = bool(ps_bat.power_plugged)
            result["summary_text"] = f"Basic Battery Info: {result['current_charge_percent']}% charge (Report error: {e})"
            result["status_level"] = "INFO"
        else:
            result["summary_text"] = f"Battery Audit Error: {e}"
            result["status_level"] = "NO_BATTERY"

    finally:
        # Guarantee cleanup of temporary xml
        if os.path.exists(xml_path):
            try:
                os.remove(xml_path)
            except Exception:
                pass

    return result


if __name__ == "__main__":
    import pprint
    print("--- Running Battery Audit Test ---")
    data = get_battery_audit()
    pprint.pprint(data)
