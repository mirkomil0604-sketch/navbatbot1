import os
import hashlib
from typing import Dict, List

from androguard.misc import AnalyzeAPK


DANGEROUS_PERMISSIONS = {
    "sms": [
        "android.permission.SEND_SMS",
        "android.permission.READ_SMS",
        "android.permission.RECEIVE_SMS",
        "android.permission.RECEIVE_MMS",
    ],
    "accessibility": [
        "android.permission.BIND_ACCESSIBILITY_SERVICE",
    ],
    "camera": [
        "android.permission.CAMERA",
    ],
    "overlay": [
        "android.permission.SYSTEM_ALERT_WINDOW",
    ],
}


def calculate_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def analyze_apk(file_path: str) -> Dict:
    a, d, dx = AnalyzeAPK(file_path)

    package_name = a.get_package() or "N/A"
    app_name = a.get_app_name() or "Noma'lum"
    sha256 = calculate_sha256(file_path)

    permissions = a.get_permissions() or []

    dangerous_found = {
        "sms": [],
        "accessibility": [],
        "camera": [],
        "overlay": [],
    }

    for perm in permissions:
        for category, perms in DANGEROUS_PERMISSIONS.items():
            if perm in perms:
                dangerous_found[category].append(perm)

    risk_score = 0
    risk_score += len(dangerous_found["sms"]) * 20
    risk_score += len(dangerous_found["accessibility"]) * 25
    risk_score += len(dangerous_found["camera"]) * 15
    risk_score += len(dangerous_found["overlay"]) * 20
    risk_score = min(risk_score, 100)

    return {
        "package_name": package_name,
        "app_name": app_name,
        "sha256": sha256,
        "permissions": dangerous_found,
        "risk_score": risk_score,
    }
