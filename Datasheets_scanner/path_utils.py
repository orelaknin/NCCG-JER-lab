from __future__ import annotations

import os
import subprocess
from pathlib import PureWindowsPath
from typing import Optional


def normalize_datasheet_path(raw_path: object, drive_letter: str = "", network_root: str = "") -> str:
    r"""Normalize a datasheet path from Excel.

    If a mapped drive letter is supplied, replace the prefix with the UNC root.
    Example: H:\docs\file.pdf -> \\server\share\docs\file.pdf
    """

    if raw_path is None:
        return ""

    path = str(raw_path).strip().strip('"').strip()
    if not path or path.lower() == "nan":
        return ""

    path = path.replace("/", "\\")

    if drive_letter and network_root:
        drive = drive_letter.strip().upper().rstrip("\\/")
        if len(drive) == 1:
            drive += ":"
        if path.upper().startswith(drive.upper()):
            suffix = path[len(drive):].lstrip("\\/")
            base = network_root.replace("/", "\\").rstrip("\\/")
            if suffix:
                return str(PureWindowsPath(base) / PureWindowsPath(suffix))
            return base

    return path


def extract_unc_share_root(network_root: str) -> str:
    r"""Return \\server\share from a UNC path."""

    root = (network_root or "").strip().strip('"').replace("/", "\\").rstrip("\\")
    if not root.startswith("\\\\"):
        return root

    parts = root.split("\\")
    # UNC looks like ['', '', 'server', 'share', 'folder', ...]
    if len(parts) >= 4:
        return f"\\\\{parts[2]}\\{parts[3]}"
    return root


def build_net_use_command(unc_share_root: str, username: str = "", password: str = "", domain: str = "") -> list[str]:
    """Build a Windows net use command for a UNC share."""

    user = username.strip()
    dom = domain.strip()
    if dom and user and "\\" not in user and "/" not in user:
        user = f"{dom}\\{user}"

    cmd = ["net", "use", unc_share_root, "/persistent:no"]
    if user:
        cmd.insert(3, f"/user:{user}")
        if password:
            cmd.insert(4, password)
    return cmd


def connect_to_share(unc_root: str, username: str = "", password: str = "", domain: str = "") -> tuple[bool, str]:
    """Authenticate to a Windows share using net use.

    Returns (success, message). If credentials are not provided, this is a no-op success.
    """

    if not (username.strip() or password.strip() or domain.strip()):
        return True, "No credentials provided; skipping share authentication."

    share_root = extract_unc_share_root(unc_root)
    if not share_root.startswith("\\\\"):
        return False, f"Cannot authenticate share because UNC root is invalid: {unc_root}"

    cmd = build_net_use_command(share_root, username=username, password=password, domain=domain)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
    except Exception as exc:  # pragma: no cover - platform issues
        return False, f"Failed to run net use: {exc}"

    output = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
    if result.returncode == 0:
        return True, f"Connected to {share_root}"

    # Common case: existing connection or already authenticated.
    lowered = output.lower()
    if "system error 1219" in lowered or "system error 85" in lowered:
        return True, output.strip() or f"Share already connected: {share_root}"

    return False, output.strip() or f"net use failed for {share_root}"
