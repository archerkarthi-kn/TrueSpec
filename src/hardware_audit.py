"""
TrueSpec: Second-Hand Laptop Inspector
Module: hardware_audit.py
Author: TrueSpec Core Systems Team

Provides anti-spoof hardware verification for CPU, RAM, Storage (S.M.A.R.T.),
GPU (PCI Device IDs), and Chassis / BIOS / Motherboard Serials.
"""

import os
import re
import sys
import winreg
import subprocess
from typing import Dict, Any, List, Optional
import psutil
import cpuinfo

# WMI initialization with fallback
try:
    import wmi
    import pythoncom
    _WMI_AVAILABLE = True
except ImportError:
    _WMI_AVAILABLE = False


def _get_wmi_client():
    """Initializes WMI client in the current thread context."""
    if not _WMI_AVAILABLE:
        return None
    try:
        pythoncom.CoInitialize()
        return wmi.WMI()
    except Exception as e:
        print(f"[HardwareAudit] WMI initialization error: {e}", file=sys.stderr)
        return None


def _clean_str(val: Optional[str]) -> str:
    """Strips whitespace, null bytes, and normalizes empty values."""
    if val is None:
        return ""
    cleaned = str(val).replace("\x00", "").strip()
    return cleaned


def _normalize_cpu_name(name: str) -> str:
    """Normalizes CPU model name for comparison (strips trademarks, extra whitespace)."""
    if not name:
        return ""
    # Remove trademarks and extra punctuation
    n = re.sub(r'[\(][^\)]*[\)]', '', name)  # removes (R), (TM) etc.
    n = re.sub(r'@.*$', '', n)  # removes clock speed suffix like '@ 2.60GHz'
    n = re.sub(r'\s+', ' ', n)
    return n.strip().lower()


def _extract_cpu_tier(name: str) -> str:
    """Extracts tier token like i3, i5, i7, i9, ryzen 3, ryzen 5, ryzen 7, ryzen 9, celeron, etc."""
    lowered = name.lower()
    for tier in [
        "core i9", "core i7", "core i5", "core i3",
        "i9", "i7", "i5", "i3",
        "ryzen 9", "ryzen 7", "ryzen 5", "ryzen 3",
        "xeon", "threadripper", "pentium", "celeron", "athlon"
    ]:
        if tier in lowered:
            return tier
    return ""


def get_cpu_audit() -> Dict[str, Any]:
    r"""
    Performs deep anti-spoof CPU verification:
    1. Reads Registry HKLM\HARDWARE\DESCRIPTION\System\CentralProcessor\0\ProcessorNameString
    2. Reads CPUID directly via cpuinfo.get_cpu_info()
    3. Cross-verifies physical core count, logical thread count, and L3 cache via WMI & psutil
    4. Detects registry spoofing and core-count contradictions.
    """
    result: Dict[str, Any] = {
        "registry_name": "Unknown",
        "cpuid_name": "Unknown",
        "wmi_name": "Unknown",
        "physical_cores": psutil.cpu_count(logical=False) or 0,
        "logical_threads": psutil.cpu_count(logical=True) or 0,
        "l3_cache_kb": 0,
        "max_clock_mhz": 0,
        "architecture": "Unknown",
        "spoof_detected": False,
        "spoof_severity": "SAFE",  # SAFE, WARNING, CRITICAL
        "spoof_reasons": [],
        "raw_flags": [],
        "details": {}
    }

    # 1. Read Registry ProcessorNameString
    try:
        reg_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            result["registry_name"] = _clean_str(val)
    except Exception as e:
        result["registry_name"] = f"Registry Read Error: {e}"

    # 2. Read CPUID directly (hardware silicon instruction)
    try:
        info = cpuinfo.get_cpu_info()
        result["cpuid_name"] = _clean_str(info.get("brand_raw", ""))
        result["architecture"] = _clean_str(info.get("arch", ""))
        result["raw_flags"] = info.get("flags", [])
        result["details"]["bits"] = info.get("bits", 64)
        result["details"]["vendor_id"] = info.get("vendor_id_raw", "")
        if "hz_actual_friendly" in info:
            result["details"]["hz_actual"] = info["hz_actual_friendly"]
    except Exception as e:
        result["cpuid_name"] = f"CPUID Error: {e}"

    # 3. Read WMI Win32_Processor
    w = _get_wmi_client()
    if w:
        try:
            procs = w.Win32_Processor()
            if procs:
                p = procs[0]
                result["wmi_name"] = _clean_str(p.Name)
                if hasattr(p, "NumberOfCores") and p.NumberOfCores:
                    result["physical_cores"] = int(p.NumberOfCores)
                if hasattr(p, "NumberOfLogicalProcessors") and p.NumberOfLogicalProcessors:
                    result["logical_threads"] = int(p.NumberOfLogicalProcessors)
                if hasattr(p, "L3CacheSize") and p.L3CacheSize:
                    result["l3_cache_kb"] = int(p.L3CacheSize)
                if hasattr(p, "MaxClockSpeed") and p.MaxClockSpeed:
                    result["max_clock_mhz"] = int(p.MaxClockSpeed)
                result["details"]["socket"] = _clean_str(getattr(p, "SocketDesignation", ""))
                result["details"]["manufacturer"] = _clean_str(getattr(p, "Manufacturer", ""))
                result["details"]["processor_id"] = _clean_str(getattr(p, "ProcessorId", ""))
        except Exception as e:
            result["details"]["wmi_error"] = str(e)

    # 4. Anti-Spoof Detection Logic
    reg_clean = result["registry_name"]
    cpuid_clean = result["cpuid_name"]

    # If CPUID failed to obtain a brand, fallback to WMI
    effective_hardware_name = cpuid_clean if "Error" not in cpuid_clean and cpuid_clean else result["wmi_name"]

    if reg_clean and effective_hardware_name and "Error" not in reg_clean and "Error" not in effective_hardware_name:
        reg_norm = _normalize_cpu_name(reg_clean)
        hw_norm = _normalize_cpu_name(effective_hardware_name)

        reg_tier = _extract_cpu_tier(reg_norm)
        hw_tier = _extract_cpu_tier(hw_norm)

        # Critical: Tier mismatch (e.g. Registry claims i7, silicon is i3 or Celeron)
        if reg_tier and hw_tier and reg_tier != hw_tier:
            result["spoof_detected"] = True
            result["spoof_severity"] = "CRITICAL"
            result["spoof_reasons"].append(
                f"TIER MISMATCH: Registry claims '{reg_tier.upper()}' but CPU silicon reports '{hw_tier.upper()}'."
            )

        # Substantial model name divergence
        # Extract model numbers (e.g. 1165G7, 7100U, 12700H)
        reg_model_matches = set(re.findall(r'[a-zA-Z0-9]{3,}', reg_norm))
        hw_model_matches = set(re.findall(r'[a-zA-Z0-9]{3,}', hw_norm))
        
        # Filter common words
        common_words = {"cpu", "processor", "intel", "amd", "core", "ryzen", "ghz", "series", "graphics", "apu"}
        reg_tokens = reg_model_matches - common_words
        hw_tokens = hw_model_matches - common_words

        # If registry has tokens that are completely foreign to hardware silicon
        if reg_tokens and hw_tokens and not (reg_tokens & hw_tokens):
            result["spoof_detected"] = True
            result["spoof_severity"] = "CRITICAL"
            result["spoof_reasons"].append(
                f"STRING MISMATCH: Registry string '{reg_clean}' contradicts CPU silicon string '{effective_hardware_name}'."
            )

        # Core count contradiction
        # E.g. Claimed modern i7/i9 usually has >= 4 or >= 6 physical cores; if physical is 2, warn
        if ("i7" in reg_tier or "i9" in reg_tier or "ryzen 7" in reg_tier or "ryzen 9" in reg_tier):
            if result["physical_cores"] <= 2 and not ("6500u" in reg_norm or "7500u" in reg_norm or "5500u" in reg_norm):
                # Older 6th/7th gen U-series i7 were 2C/4T, but if modern tier claims 8-core and it's 2-core:
                result["spoof_reasons"].append(
                    f"TOPOLOGY WARNING: Claimed high-tier processor '{reg_clean}' only has {result['physical_cores']} physical cores ({result['logical_threads']} threads)."
                )
                if result["spoof_severity"] != "CRITICAL":
                    result["spoof_severity"] = "WARNING"

    return result


def get_ram_audit() -> Dict[str, Any]:
    """
    Audits RAM architecture:
    - Total installed GB
    - Physical memory slots used vs total slots on motherboard
    - Channel mode (Single vs Dual / Multi Channel)
    - Per-stick speed (MHz), capacity, manufacturer, slot locator
    """
    total_bytes = psutil.virtual_memory().total
    total_gb = round(total_bytes / (1024 ** 3), 1)

    result: Dict[str, Any] = {
        "total_gb": total_gb,
        "total_bytes": total_bytes,
        "slots_used": 0,
        "slots_total": 0,
        "channel_mode": "Single-Channel",
        "sticks": [],
        "summary_text": f"{total_gb} GB RAM"
    }

    w = _get_wmi_client()
    if w:
        # Check total slots from Win32_PhysicalMemoryArray
        try:
            arrays = w.Win32_PhysicalMemoryArray()
            if arrays:
                total_slots = sum(int(a.MemoryDevices or 0) for a in arrays)
                result["slots_total"] = max(total_slots, 1)
        except Exception as e:
            result["slots_total"] = 0

        # Check sticks from Win32_PhysicalMemory
        try:
            mem_sticks = w.Win32_PhysicalMemory()
            slots_used = len(mem_sticks)
            result["slots_used"] = slots_used

            speeds = []
            for s in mem_sticks:
                cap_gb = round(int(s.Capacity or 0) / (1024 ** 3), 1)
                speed = int(getattr(s, "ConfiguredClockSpeed", None) or getattr(s, "Speed", None) or 0)
                if speed > 0:
                    speeds.append(speed)
                stick_info = {
                    "capacity_gb": cap_gb,
                    "speed_mhz": speed,
                    "manufacturer": _clean_str(getattr(s, "Manufacturer", "Unknown")),
                    "part_number": _clean_str(getattr(s, "PartNumber", "")),
                    "locator": _clean_str(getattr(s, "DeviceLocator", getattr(s, "BankLabel", "DIMM"))),
                    "form_factor": getattr(s, "FormFactor", 0)
                }
                result["sticks"].append(stick_info)

            # Fallback if slots_total was 0 or less than slots_used
            if result["slots_total"] < slots_used:
                result["slots_total"] = slots_used

            # Channel detection
            if slots_used >= 2:
                result["channel_mode"] = "Dual-Channel"
            else:
                result["channel_mode"] = "Single-Channel"

            avg_speed = int(sum(speeds) / len(speeds)) if speeds else 0
            slots_txt = f"{slots_used} of {result['slots_total']} slots used"
            speed_txt = f" @ {avg_speed} MHz" if avg_speed > 0 else ""
            result["summary_text"] = f"{total_gb} GB ({result['channel_mode']}, {slots_txt}{speed_txt})"

        except Exception as e:
            result["summary_text"] = f"{total_gb} GB RAM (WMI error: {e})"
    else:
        result["summary_text"] = f"{total_gb} GB RAM"

    return result


def get_storage_audit() -> Dict[str, Any]:
    """
    Audits physical drives:
    - Drive Model, Total Capacity
    - Media Type (NVMe SSD, SATA SSD, HDD)
    - S.M.A.R.T. status (OK vs Failing / Pred Fail)
    - Primary OS drive assessment
    """
    result: Dict[str, Any] = {
        "drives": [],
        "all_smart_ok": True,
        "has_ssd": False,
        "primary_is_ssd": True,  # Heuristic assessment
        "summary_text": ""
    }

    # Query PowerShell Get-Disk for bus types (NVMe / SATA / USB)
    bus_type_map = {}
    try:
        ps_cmd = 'powershell -NoProfile -Command "Get-Disk | Select-Object Number, FriendlyName, BusType, HealthStatus | ConvertTo-Json"'
        proc = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        if proc.returncode == 0 and proc.stdout.strip():
            import json
            data = json.loads(proc.stdout)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                name = item.get("FriendlyName", "").strip()
                bus = item.get("BusType", "").strip()
                if name:
                    bus_type_map[name.lower()] = bus
    except Exception:
        pass

    w = _get_wmi_client()
    if w:
        try:
            disks = w.Win32_DiskDrive()
            for d in disks:
                model = _clean_str(d.Model)
                size_bytes = int(d.Size or 0)
                size_gb = round(size_bytes / (1024 ** 3), 1)
                status = _clean_str(d.Status) or "OK"
                interface = _clean_str(d.InterfaceType)
                media = _clean_str(d.MediaType)

                # S.M.A.R.T. health check
                is_smart_ok = (status.upper() == "OK")
                if not is_smart_ok:
                    result["all_smart_ok"] = False

                # Media Type classification
                lowered_model = model.lower()
                bus_type = bus_type_map.get(lowered_model, "")

                if "nvme" in lowered_model or bus_type.lower() == "nvme" or "pcie" in lowered_model:
                    media_type = "NVMe SSD"
                    is_ssd = True
                elif "ssd" in lowered_model or "solid state" in media.lower() or "flash" in lowered_model or bus_type.lower() == "sata" and "m.2" in lowered_model:
                    media_type = "SATA SSD"
                    is_ssd = True
                elif "hdd" in lowered_model or "hard disk" in media.lower() or "rotational" in lowered_model:
                    media_type = "HDD (Mechanical)"
                    is_ssd = False
                else:
                    # Heuristic default based on capacity or model name
                    if "sandisk" in lowered_model or "samsung" in lowered_model or "crucial" in lowered_model or "kingston" in lowered_model or "wd blue sn" in lowered_model:
                        media_type = "SSD"
                        is_ssd = True
                    else:
                        media_type = "Storage Drive"
                        is_ssd = True if size_gb <= 1000 else False

                if is_ssd:
                    result["has_ssd"] = True

                drive_entry = {
                    "model": model,
                    "size_gb": size_gb,
                    "media_type": media_type,
                    "interface": bus_type or interface,
                    "smart_status": status,
                    "is_smart_ok": is_smart_ok,
                    "pnp_device_id": _clean_str(getattr(d, "PNPDeviceID", ""))
                }
                result["drives"].append(drive_entry)

            # Determine primary drive type (Drive 0 or largest SSD)
            if result["drives"]:
                # If first drive or any drive is SSD, consider primary is SSD
                result["primary_is_ssd"] = any(d["media_type"].endswith("SSD") for d in result["drives"])
                summary_parts = [f"{d['size_gb']}GB {d['media_type']} ({d['smart_status']})" for d in result["drives"]]
                result["summary_text"] = " | ".join(summary_parts)
            else:
                result["summary_text"] = "No physical drives detected"

        except Exception as e:
            result["summary_text"] = f"Storage audit error: {e}"
    else:
        result["summary_text"] = "WMI Unavailable"

    return result


def get_gpu_audit() -> Dict[str, Any]:
    """
    Audits GPUs and display adapters:
    - Real VRAM (AdapterRAM)
    - Full PNP Device ID (PCI\\VEN_...&DEV_...) to detect fake flashed GPUs
    - Identifies Dedicated vs Integrated GPUs
    """
    result: Dict[str, Any] = {
        "adapters": [],
        "has_dedicated_gpu": False,
        "summary_text": ""
    }

    w = _get_wmi_client()
    if w:
        try:
            controllers = w.Win32_VideoController()
            for c in controllers:
                name = _clean_str(c.Name)
                vram_bytes = int(getattr(c, "AdapterRAM", 0) or 0)
                # AdapterRAM may overflow 32-bit signed int on some systems (e.g. negative or 4GB clamped)
                if vram_bytes < 0:
                    vram_bytes += (1 << 32)
                vram_mb = round(vram_bytes / (1024 ** 2), 0)
                vram_gb = round(vram_bytes / (1024 ** 3), 1)

                pnp_id = _clean_str(getattr(c, "PNPDeviceID", ""))
                driver_ver = _clean_str(getattr(c, "DriverVersion", "Unknown"))
                video_proc = _clean_str(getattr(c, "VideoProcessor", ""))

                # Categorize GPU
                lowered = name.lower()
                is_dedicated = False
                if "nvidia" in lowered or "geforce" in lowered or "rtx" in lowered or "gtx" in lowered or "quadro" in lowered:
                    is_dedicated = True
                elif "radeon rx" in lowered or "radeon pro" in lowered or "discrete" in lowered:
                    is_dedicated = True
                elif "intel" in lowered or "iris" in lowered or "uhd" in lowered or "hd graphics" in lowered or "radeon graphics" in lowered:
                    is_dedicated = False

                if is_dedicated:
                    result["has_dedicated_gpu"] = True

                gpu_entry = {
                    "name": name,
                    "vram_mb": vram_mb,
                    "vram_gb": vram_gb,
                    "pnp_device_id": pnp_id,
                    "driver_version": driver_ver,
                    "video_processor": video_proc,
                    "is_dedicated": is_dedicated
                }
                result["adapters"].append(gpu_entry)

            if result["adapters"]:
                parts = [f"{a['name']} ({a['vram_gb']}GB VRAM)" if a['vram_gb'] >= 1 else a['name'] for a in result["adapters"]]
                result["summary_text"] = " + ".join(parts)
            else:
                result["summary_text"] = "No display adapters detected"

        except Exception as e:
            result["summary_text"] = f"GPU audit error: {e}"
    else:
        result["summary_text"] = "WMI Unavailable"

    return result


def get_motherboard_bios_audit() -> Dict[str, Any]:
    """
    Audits BIOS, Chassis Serial, and Motherboard:
    - Win32_BIOS SerialNumber
    - Win32_ComputerSystemProduct UUID & Model
    - Win32_BaseBoard Product & Serial
    - Detects generic/refurbished/flashed motherboard strings
    """
    result: Dict[str, Any] = {
        "model_name": "Unknown System",
        "vendor": "Unknown",
        "chassis_serial": "Unknown",
        "bios_serial": "Unknown",
        "bios_version": "Unknown",
        "bios_date": "Unknown",
        "uuid": "Unknown",
        "motherboard_model": "Unknown",
        "motherboard_serial": "Unknown",
        "suspicious_serial": False,
        "serial_notes": []
    }

    w = _get_wmi_client()
    if w:
        # Win32_BIOS
        try:
            bioss = w.Win32_BIOS()
            if bioss:
                b = bioss[0]
                result["bios_serial"] = _clean_str(getattr(b, "SerialNumber", ""))
                result["bios_version"] = _clean_str(getattr(b, "SMBIOSBIOSVersion", ""))
                result["bios_date"] = _clean_str(getattr(b, "ReleaseDate", ""))
        except Exception:
            pass

        # Win32_ComputerSystemProduct
        try:
            csps = w.Win32_ComputerSystemProduct()
            if csps:
                p = csps[0]
                result["model_name"] = _clean_str(getattr(p, "Name", ""))
                result["vendor"] = _clean_str(getattr(p, "Vendor", ""))
                result["chassis_serial"] = _clean_str(getattr(p, "IdentifyingNumber", ""))
                result["uuid"] = _clean_str(getattr(p, "UUID", ""))
        except Exception:
            pass

        # Win32_BaseBoard
        try:
            boards = w.Win32_BaseBoard()
            if boards:
                bb = boards[0]
                result["motherboard_model"] = _clean_str(getattr(bb, "Product", ""))
                result["motherboard_serial"] = _clean_str(getattr(bb, "SerialNumber", ""))
        except Exception:
            pass

    # Serial integrity check: flag placeholders common on flashed/swapped boards
    suspicious_patterns = ["default string", "to be filled by o.e.m.", "none", "00000000", "system serial number", "chassis serial number"]
    effective_serial = result["chassis_serial"].lower()
    for pat in suspicious_patterns:
        if pat in effective_serial:
            result["suspicious_serial"] = True
            result["serial_notes"].append(
                f"Generic/Placeholder Serial detected: '{result['chassis_serial']}'. The motherboard may have been replaced, flashed, or refurbished."
            )
            break

    return result


def get_full_hardware_audit() -> Dict[str, Any]:
    """Runs all hardware audits and aggregates into a single dictionary."""
    return {
        "cpu": get_cpu_audit(),
        "ram": get_ram_audit(),
        "storage": get_storage_audit(),
        "gpu": get_gpu_audit(),
        "system": get_motherboard_bios_audit()
    }


if __name__ == "__main__":
    import pprint
    print("--- Running Hardware Audit Test ---")
    data = get_full_hardware_audit()
    pprint.pprint(data)
