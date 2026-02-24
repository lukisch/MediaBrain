"""
config.py
Zentrale Konfigurationen für MediaBrain:
- Pfade
- Standardwerte
- Benutzer-Einstellungen
- Provider-Konfiguration
"""

from pathlib import Path
import json
import shutil
import os
import time


# ============================================================
# 1. Pfade
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "media_brain.db"
LOG_PATH = BASE_DIR / "logs" / "app.log"
SETTINGS_PATH = BASE_DIR / "settings.json"


# ============================================================
# 2. Default-Einstellungen
# ============================================================

DEFAULT_SETTINGS = {
    "ui": {
        "theme": "light",
        "window_width": 1200,
        "window_height": 800
    },
    "providers": {
        "netflix": {"preferred_open_method": "browser"},
        "youtube": {"preferred_open_method": "browser"},
        "spotify": {"preferred_open_method": "app"},
        "local": {"preferred_open_method": "local"}
    },
    "library_sorting": {
        "movie": "last_opened",
        "series": "last_opened",
        "music": "last_opened",
        "clip": "last_opened",
        "podcast": "last_opened",
        "audiobook": "last_opened"
    },
    "file_indexer": {
        "enabled": True,
        "watch_paths": [
            str(Path.home() / "Music"),
            str(Path.home() / "Videos"),
            str(Path.home() / "Downloads")
        ]
    },
    "auto_fetch_metadata": True,
    "allow_file_deletion": False
}


# ============================================================
# 3. Settings Manager
# ============================================================

class Config:
    """
    Lädt und speichert Benutzer-Einstellungen.
    Falls settings.json nicht existiert → Default-Werte verwenden.
    """

    def __init__(self):
        """
        Initialisiert Config Manager und lädt Einstellungen.

        Lädt automatisch settings.json beim Start.
        Falls Datei fehlt oder korrupt: Recovery aus Backup oder Defaults.
        """
        self.settings = {}
        self.load()

    def load(self):
        """
        Lädt settings.json.
        Features:
        - Recovery: Falls JSON korrupt, versuche .bak
        - Fallback: Falls alles scheitert, Defaults
        """
        # 1. Versuch: Normale Datei laden
        if SETTINGS_PATH.exists():
            try:
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
                return  # Erfolg
            except Exception as e:
                print(f"[Config] settings.json korrupt: {e}")
        
        # 2. Versuch: Backup laden
        backup_path = SETTINGS_PATH.with_suffix(".json.bak")
        if backup_path.exists():
            try:
                print(f"[Config] Versuche Recovery aus {backup_path.name}...")
                with open(backup_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
                # Backup ist gut -> Wiederherstellen
                self.save()
                return  # Erfolg
            except Exception as e:
                print(f"[Config] Backup auch korrupt: {e}")

        # 3. Fallback: Defaults
        print("[Config] Lade Defaults (keine gultige Config gefunden).")
        self.settings = DEFAULT_SETTINGS.copy()
        self.save()

    def save(self):
        """
        Speichert Einstellungen sicher.
        Features:
        - Backup: Erstellt settings.json.bak vor Speichern
        - Atomic Write: Schreibt in .tmp und benennt um
        """
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Backup erstellen (falls Original existiert)
        if SETTINGS_PATH.exists():
            try:
                backup_path = SETTINGS_PATH.with_suffix(".json.bak")
                shutil.copy2(SETTINGS_PATH, backup_path)
            except Exception as e:
                print(f"[Config] Backup fehlgeschlagen: {e}")

        # 2. Atomic Write
        tmp_path = SETTINGS_PATH.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            
            # Atomic Rename with Retry (OneDrive fix)
            max_retries = 5
            for i in range(max_retries):
                try:
                    if SETTINGS_PATH.exists():
                        os.replace(tmp_path, SETTINGS_PATH)
                    else:
                        os.rename(tmp_path, SETTINGS_PATH)
                    break 
                except OSError as e:
                    if i == max_retries - 1:
                        raise e
                    time.sleep(0.2)
            
        except Exception as e:
            print(f"[Config] Speichern fehlgeschlagen: {e}")
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except:
                    pass

    def get(self, path, default=None):
        """
        Zugriff auf verschachtelte Einstellungen:
        config.get("providers.netflix.preferred_open_method")
        """
        keys = path.split(".")
        value = self.settings
        for key in keys:
            if key not in value:
                return default
            value = value[key]
        return value

    def set(self, path, value):
        """
        Setzt verschachtelte Einstellungen:
        config.set("providers.netflix.preferred_open_method", "app")
        """
        keys = path.split(".")
        obj = self.settings
        for key in keys[:-1]:
            if key not in obj:
                obj[key] = {}
            obj = obj[key]
        obj[keys[-1]] = value
        self.save()


# ============================================================
# 4. Globale Config-Instanz
# ============================================================

config = Config()
