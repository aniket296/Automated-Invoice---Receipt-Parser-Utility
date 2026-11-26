"""Vendor Profile persistence manager and keyword matcher."""

import json
from pathlib import Path
from typing import Optional
from src.models.vendor_rule import VendorProfile
from src.utils.config import get_vendor_profiles_path
from src.utils.logger import get_logger

logger = get_logger()


class VendorProfileStore:
    """Manages loading, saving, matching, and updating custom VendorProfile rules."""

    def __init__(self, json_path: Optional[Path | str] = None) -> None:
        self.json_path: Path = Path(json_path) if json_path else get_vendor_profiles_path()
        self.profiles: list[VendorProfile] = []
        self.load()

    def load(self) -> list[VendorProfile]:
        """Loads vendor profiles from the JSON store on disk."""
        if not self.json_path.exists():
            self.profiles = []
            return self.profiles
        try:
            raw = self.json_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, list):
                self.profiles = [
                    VendorProfile.from_dict(item)
                    for item in data
                    if isinstance(item, dict) and item.get("vendor_name")
                ]
            else:
                self.profiles = []
        except Exception as exc:
            logger.warning("Failed to load vendor profiles from %s: %s", self.json_path, exc)
            self.profiles = []
        return self.profiles

    def save(self) -> None:
        """Persists current vendor profiles to disk as formatted JSON."""
        try:
            self.json_path.parent.mkdir(parents=True, exist_ok=True)
            payload = [p.to_dict() for p in self.profiles]
            self.json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.error("Failed to save vendor profiles to %s: %s", self.json_path, exc)

    def get_all_profiles(self) -> list[VendorProfile]:
        """Returns a copy of all configured vendor profiles."""
        return list(self.profiles)

    def match_vendor(self, raw_text: str) -> Optional[VendorProfile]:
        """Returns the first profile whose match_keywords appear in raw_text (case-insensitive)."""
        if not raw_text:
            return None
        lowered = raw_text.lower()
        for profile in self.profiles:
            for kw in profile.match_keywords:
                kw_clean = kw.strip().lower()
                if kw_clean and kw_clean in lowered:
                    return profile
        return None

    def add_or_update_profile(self, profile: VendorProfile) -> None:
        """Adds a new VendorProfile or updates an existing one with the same vendor_name."""
        target_name = profile.vendor_name.strip().lower()
        for idx, existing in enumerate(self.profiles):
            if existing.vendor_name.strip().lower() == target_name:
                self.profiles[idx] = profile
                self.save()
                return
        self.profiles.append(profile)
        self.save()

    def delete_profile(self, vendor_name: str) -> bool:
        """Deletes a vendor profile by name (case-insensitive). Returns True if removed."""
        target_name = vendor_name.strip().lower()
        initial_len = len(self.profiles)
        self.profiles = [
            p for p in self.profiles if p.vendor_name.strip().lower() != target_name
        ]
        if len(self.profiles) < initial_len:
            self.save()
            return True
        return False
