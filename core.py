"""
core.py
Zentrale Logik für MediaBrain:
- SQLite-Datenbank
- MediaItem-Datenmodell
- MediaManager (CRUD, Favoriten, Sortierung)
- BlacklistManager (Sperrlogik)
- EventProcessor (Events vom Hintergrundprozess)
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union, Tuple, List

# Optional imports (für Tests ohne externe Dependencies)
try:
    import metadata_v2 as metadata  # Upgraded to v2 with TMDb/OMDb/MusicBrainz
    HAS_METADATA = True
except ImportError:
    HAS_METADATA = False

try:
    import config as cfg  # Fuer auto_fetch_metadata Toggle
    HAS_CONFIG = True
except ImportError:
    HAS_CONFIG = False

# ============================================================
# 1. Datenbank
# ============================================================

class Database:
    def __init__(self, db_path="media_brain.db"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._setup()

    def _setup(self):
        """Initialisiert die Datenbank und Tabellen."""
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            source TEXT NOT NULL,
            provider_id TEXT,
            length_seconds INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_opened_at TEXT,
            open_method TEXT,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            is_local_file INTEGER NOT NULL DEFAULT 0,
            local_path TEXT,
            description TEXT,
            thumbnail_url TEXT,
            season INTEGER,
            episode INTEGER,
            artist TEXT,
            album TEXT,
            channel TEXT,

            blacklist_flag INTEGER NOT NULL DEFAULT 0,
            blacklisted_at TEXT,
            procedure_code INTEGER NOT NULL DEFAULT 0,

            UNIQUE(provider_id, source)
        );
        """)

        # Indexe für Performance
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_media_last_opened ON media_items(last_opened_at);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_media_type ON media_items(type);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_media_favorite ON media_items(is_favorite);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_media_blacklist ON media_items(blacklist_flag);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_media_title ON media_items(title);")

        # Composite Indizes für häufige Kombinationen
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_media_type_blacklist ON media_items(type, blacklist_flag);")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_media_favorite_blacklist ON media_items(is_favorite, blacklist_flag);")

        self.conn.commit()

    def execute(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """
        Führt eine SQL-Query aus und committed die Änderungen.

        Args:
            query: SQL-Query String
            params: Tuple mit Query-Parametern (optional)

        Returns:
            sqlite3.Cursor Objekt
        """
        cur = self.conn.execute(query, params)
        self.conn.commit()
        return cur

    def fetchall(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """
        Führt eine SELECT-Query aus und gibt alle Ergebnisse zurück.

        Args:
            query: SQL-Query String
            params: Tuple mit Query-Parametern (optional)

        Returns:
            Liste von sqlite3.Row Objekten
        """
        return self.conn.execute(query, params).fetchall()

    def fetchone(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        """
        Führt eine SELECT-Query aus und gibt das erste Ergebnis zurück.

        Args:
            query: SQL-Query String
            params: Tuple mit Query-Parametern (optional)

        Returns:
            sqlite3.Row Objekt oder None
        """
        return self.conn.execute(query, params).fetchone()


# ============================================================
# 2. MediaItem Datenmodell
# ============================================================

class MediaItem:
    """
    Datenmodell für ein einzelnes Media-Item.

    Konvertiert sqlite3.Row in ein Python-Objekt mit typisierten Feldern.
    Unterstützt Filme, Serien, Musik, Clips, Podcasts, Hörbücher, Dokumente.

    Attributes:
        id: Eindeutige ID (Auto-Increment)
        title: Anzeigename
        type: Medientyp (movie, series, music, clip, podcast, audiobook, document)
        source: Provider-ID (netflix, youtube, spotify, local, etc.)
        provider_id: Provider-spezifische ID
        is_favorite: Favoriten-Flag
        is_local_file: Lokale Datei oder Online-Quelle
        blacklist_flag: Blacklist-Status (0 = nicht gesperrt, 1 = gesperrt)
        procedure_code: Blacklist-Dauer Code (0-6)
    """
    def __init__(self, row):
        self.id = row["id"]
        self.title = row["title"]
        self.type = row["type"]
        self.source = row["source"]
        self.provider_id = row["provider_id"]
        self.length_seconds = row["length_seconds"]
        self.created_at = row["created_at"]
        self.last_opened_at = row["last_opened_at"]
        self.open_method = row["open_method"]
        self.is_favorite = bool(row["is_favorite"])
        self.is_local_file = bool(row["is_local_file"])
        self.local_path = row["local_path"]
        self.description = row["description"]
        self.thumbnail_url = row["thumbnail_url"]
        self.season = row["season"]
        self.episode = row["episode"]
        self.artist = row["artist"]
        self.album = row["album"]
        self.channel = row["channel"]
        self.blacklist_flag = row["blacklist_flag"]
        self.blacklisted_at = row["blacklisted_at"]
        self.procedure_code = row["procedure_code"]


# ============================================================
# 3. Blacklist Manager
# ============================================================

class BlacklistManager:
    """
    Verwaltet Blacklist-Status:
    - procedure_code 0 = keine Sperre
    - 1 = 1 Tag
    - 2 = 1 Woche
    - 3 = 1 Monat
    - 4 = 3 Monate
    - 5 = 1 Jahr
    - 6 = für immer
    """

    def __init__(self, db: Database):
        self.db = db

    def _expiry_date(self, start: datetime, code: int):
        if code == 1:
            return start + timedelta(days=1)
        if code == 2:
            return start + timedelta(weeks=1)
        if code == 3:
            return start + timedelta(days=30)
        if code == 4:
            return start + timedelta(days=90)
        if code == 5:
            return start + timedelta(days=365)
        if code == 6:
            return None  # für immer
        return None

    def refresh_blacklist(self):
        """Prüft beim Start, ob Blacklist-Einträge abgelaufen sind."""
        rows = self.db.fetchall("""
            SELECT id, blacklisted_at, procedure_code
            FROM media_items
            WHERE blacklist_flag = 1
        """)

        for row in rows:
            if not row["blacklisted_at"]:
                continue

            start = datetime.fromisoformat(row["blacklisted_at"])
            expiry = self._expiry_date(start, row["procedure_code"])

            if expiry and datetime.now() > expiry:
                # Sperre abgelaufen
                self.db.execute("""
                    UPDATE media_items
                    SET blacklist_flag = 0,
                        procedure_code = 0,
                        blacklisted_at = NULL
                    WHERE id = ?
                """, (row["id"],))

    def set_blacklist(self, item_id: int, enabled: bool, procedure_code: int = 6):
        """Setzt oder entfernt Blacklist-Status."""
        if enabled:
            self.db.execute("""
                UPDATE media_items
                SET blacklist_flag = 1,
                    blacklisted_at = ?,
                    procedure_code = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), procedure_code, item_id))
        else:
            self.db.execute("""
                UPDATE media_items
                SET blacklist_flag = 0,
                    blacklisted_at = NULL,
                    procedure_code = 0
                WHERE id = ?
            """, (item_id,))


# ============================================================
# 4. MediaManager
# ============================================================

class MediaManager:
    def __init__(self, db: Database):
        self.db = db

    def get_by_provider(self, provider_id: str, source: str) -> Optional['MediaItem']:
        """
        Sucht ein Medium anhand von provider_id und source.

        Args:
            provider_id: Eindeutige ID vom Provider (z.B. YouTube Video-ID)
            source: Provider-Name (z.B. "youtube", "netflix", "spotify")

        Returns:
            MediaItem Objekt oder None wenn nicht gefunden
        """
        row = self.db.fetchone("""
            SELECT * FROM media_items
            WHERE provider_id = ? AND source = ?
        """, (provider_id, source))
        return MediaItem(row) if row else None

    def add_or_update(self, data: dict, origin="external"):
        """
        Fügt ein neues Medium hinzu oder aktualisiert ein bestehendes.

        Args:
            data: Dict mit Medien-Daten (muss mindestens 'type', 'source', 'provider_id' enthalten)
            origin: "external" (von Providers) oder "internal" (manuelle Eingabe)

        Raises:
            ValueError: Wenn required fields fehlen oder invalid sind
        """
        # === INPUT VALIDATION ===
        # Required fields prüfen
        required_fields = ["type", "source", "provider_id"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Required field missing: {field}")
            if not data[field]:  # Prüfe auf None oder leeren String
                raise ValueError(f"Required field cannot be empty: {field}")

        # Type muss aus erlaubten Werten sein
        allowed_types = ["movie", "series", "music", "clip", "podcast", "audiobook", "document", "file"]
        if data["type"] not in allowed_types:
            raise ValueError(f"Invalid type: {data['type']}. Allowed: {allowed_types}")

        # Source darf keine SQL-kritischen Zeichen enthalten (zusätzliche Sicherheit)
        if any(c in str(data["source"]) for c in ["'", '"', ";", "--"]):
            raise ValueError("Source contains invalid characters")

        # Title sollte begrenzt sein
        if "title" in data and data["title"]:
            if len(data["title"]) > 500:
                data["title"] = data["title"][:497] + "..."

        # length_seconds muss numerisch sein (falls angegeben)
        if "length_seconds" in data and data["length_seconds"] is not None:
            try:
                data["length_seconds"] = int(data["length_seconds"])
            except (ValueError, TypeError):
                raise ValueError(f"length_seconds must be numeric, got: {data['length_seconds']}")

            # Negativprüfung nach erfolgreicher Konvertierung
            if data["length_seconds"] < 0:
                raise ValueError("length_seconds cannot be negative")

        # season/episode müssen numerisch sein (falls angegeben)
        for field in ["season", "episode"]:
            if field in data and data[field] is not None:
                try:
                    data[field] = int(data[field])
                except (ValueError, TypeError):
                    raise ValueError(f"{field} must be numeric, got: {data[field]}")

                # Negativprüfung nach erfolgreicher Konvertierung
                if data[field] < 0:
                    raise ValueError(f"{field} cannot be negative")

        # === END VALIDATION ===

        existing = self.get_by_provider(data["provider_id"], data["source"])

        if existing and existing.blacklist_flag == 1 and origin == "external":
            return

        if existing:
            self.db.execute("""
                UPDATE media_items
                SET last_opened_at = ?,
                    open_method = COALESCE(?, open_method)
                WHERE id = ?
            """, (datetime.now().isoformat(), data.get("open_method"), existing.id))
            return

        # --- METADATEN NUR LADEN, WENN WIR EINE ECHTE ID HABEN ---
        # Wir prüfen auf das Flag 'has_real_id', das wir in providers.py gesetzt haben.
        # Wenn es fehlt (LocalProvider), nehmen wir False an, außer es ist explizit True.
        
        # Pruefe auto_fetch_metadata Setting (nur wenn config verfügbar)
        auto_fetch_enabled = HAS_CONFIG and cfg.config.get("auto_fetch_metadata", True)
        should_fetch_meta = HAS_METADATA and auto_fetch_enabled and data.get("has_real_id", False) and origin == "external"

        if should_fetch_meta:
            url_to_check = None
            if data["source"] == "youtube":
                url_to_check = f"https://www.youtube.com/watch?v={data['provider_id']}"
            elif data["source"] == "netflix":
                url_to_check = f"https://www.netflix.com/watch/{data['provider_id']}"
            elif data["source"] == "spotify":
                url_to_check = f"https://open.spotify.com/track/{data['provider_id']}"

            if url_to_check:
                try:
                    meta = metadata.fetch_metadata(url_to_check)
                    if meta:
                        if meta.get("title"): data["title"] = meta["title"]
                        if meta.get("description"): data["description"] = meta["description"]
                        if meta.get("thumbnail_url"): data["thumbnail_url"] = meta["thumbnail_url"]
                except Exception as e:
                    print(f"[MediaManager] Warnung: Metadaten-Fehler: {e}")

        # Insert (DB)
        try:
            self.db.execute("""
                INSERT INTO media_items (
                    title, type, source, provider_id,
                    length_seconds, last_opened_at,
                    open_method, is_local_file, local_path,
                    description, thumbnail_url, season, episode,
                    artist, album, channel
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("title", "Unbekannt"),
                data["type"],
                data["source"],
                data["provider_id"],
                data.get("length_seconds"),
                datetime.now().isoformat(),
                data.get("open_method", "auto"),
                1 if data.get("is_local_file") else 0,
                data.get("local_path"),
                data.get("description"),
                data.get("thumbnail_url"),
                data.get("season"),
                data.get("episode"),
                data.get("artist"),
                data.get("album"),
                data.get("channel"),
            ))
            # print(f"[DB] Erfolgreich gespeichert: {data['title']}") # Debug Print
        except Exception as e:
            print(f"[DB] INSERT ERROR: {e}")
    def list_by_type(self, media_type):
        """
        Gibt eine Liste von MediaItems für einen bestimmten Typ (movie, music, etc.) zurück.
        Filtert geblacklistete Einträge heraus.
        Sortiert Favoriten nach oben.
        """
        rows = self.db.fetchall("""
            SELECT *
            FROM media_items
            WHERE type = ? AND blacklist_flag = 0
            ORDER BY is_favorite DESC, last_opened_at DESC
        """, (media_type,))
        
        # Wandelt die Datenbank-Zeilen in MediaItem-Objekte um
        return [MediaItem(r) for r in rows]
# ============================================================
# 5. EventProcessor
# ============================================================

class EventProcessor:
    """
    Verarbeitet Events IM MAIN THREAD.
    Hintergrundprozesse dürfen NICHT direkt die DB anfassen.
    """

    def __init__(self, media_manager):
        self.media_manager = media_manager
        self.queue = None          # Wird vom AppController gesetzt
        self.on_data_changed = None  # Wird vom AppController gesetzt (wird aber hier nicht mehr direkt gefeuert)

    def process_event(self, event):
        """
        Wird IM MAIN THREAD ausgeführt.
        Verarbeitet Daten, aber aktualisiert NICHT sofort die GUI.
        Das macht jetzt der Controller in MediaBrain.py gebündelt (Batch-Processing),
        um Abstürze bei vielen Dateien zu verhindern.
        """
        # Daten in die Datenbank schreiben
        self.media_manager.add_or_update(event, origin=event.get("origin", "external"))

        # WICHTIG: Die direkte GUI-Aktualisierung wurde hier ENTFERNT.
        # if self.on_data_changed:
        #     self.on_data_changed()

# ============================================================
# 6. OpenHandler – Öffnen von Medien
# ============================================================

import webbrowser
import os
import subprocess
import platform

# config bereits oben importiert (optional)


class OpenHandler:
    def __init__(self, media_manager: MediaManager):
        self.media_manager = media_manager

    # --------------------------------------------------------
    # Hauptfunktion
    # --------------------------------------------------------
    def open_item(self, item: MediaItem):
        """
        Öffnet ein Medium mit der bevorzugten Methode.

        Args:
            item: MediaItem Objekt das geöffnet werden soll

        Öffnet lokale Dateien mit OS-Standard-App,
        Online-Inhalte per Browser oder Deep-Link (je nach Konfiguration).
        Speichert die verwendete Methode und aktualisiert last_opened_at.
        """
        provider = item.source
        preferred = "auto"  # Default
        if HAS_CONFIG:
            preferred = config.config.get(f"providers.{provider}.preferred_open_method", "auto")

        # Auto = letzter verwendeter Weg
        if preferred == "auto" and item.open_method:
            preferred = item.open_method

        # Lokale Dateien
        if item.is_local_file:
            return self._open_local(item)

        # Online-Dienste
        if preferred == "browser":
            return self._open_in_browser(item)

        if preferred == "app":
            return self._open_in_app(item)

        # Fallback
        return self._open_in_browser(item)

    # --------------------------------------------------------
    # Browser öffnen
    # --------------------------------------------------------
    def _open_in_browser(self, item: MediaItem):
        url = self._build_browser_url(item)
        if url:
            webbrowser.open(url)
            self._update_open_method(item, "browser")

    # --------------------------------------------------------
    # App öffnen (Deep Link)
    # --------------------------------------------------------
    def _open_in_app(self, item: MediaItem):
        deep = self._build_deep_link(item)
        if not deep:
            return self._open_in_browser(item)

        system = platform.system()

        try:
            if system == "Windows":
                os.startfile(deep)
            elif system == "Darwin":  # macOS
                subprocess.Popen(["open", deep])
            else:  # Linux
                subprocess.Popen(["xdg-open", deep])

            self._update_open_method(item, "app")
        except Exception:
            # Fallback: Browser
            self._open_in_browser(item)

    # --------------------------------------------------------
    # Lokale Dateien öffnen
    # --------------------------------------------------------
    def _open_local(self, item: MediaItem):
        path = item.local_path
        if not path:
            return

        system = platform.system()

        try:
            if system == "Windows":
                os.startfile(path)
            elif system == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

            self._update_open_method(item, "local")
        except Exception as e:
            print("Fehler beim Öffnen lokaler Datei:", e)

    # --------------------------------------------------------
    # Hilfsfunktionen
    # --------------------------------------------------------
    def _build_browser_url(self, item: MediaItem):
        if item.source == "netflix":
            return f"https://www.netflix.com/watch/{item.provider_id}"
        if item.source == "youtube":
            return f"https://www.youtube.com/watch?v={item.provider_id}"
        if item.source == "spotify":
            return f"https://open.spotify.com/track/{item.provider_id}"
        return None

    def _build_deep_link(self, item: MediaItem):
        if item.source == "netflix":
            return f"netflix://title/{item.provider_id}"
        if item.source == "spotify":
            return f"spotify:track:{item.provider_id}"
        if item.source == "youtube":
            return f"vnd.youtube:{item.provider_id}"
        return None

    def _update_open_method(self, item: MediaItem, method: str):
        self.media_manager.db.execute(
            "UPDATE media_items SET open_method = ?, last_opened_at = ? WHERE id = ?",
            (method, datetime.now().isoformat(), item.id)
        )
