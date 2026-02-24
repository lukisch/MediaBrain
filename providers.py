"""
providers.py
Erkennt Medien anhand von URL oder Fenstertitel.
Version: 2.0 - Erweitert mit Disney+, Amazon Prime, Apple TV+
"""
import re
from pathlib import Path

# ============================================================
# Basis-Klasse
# ============================================================
class BaseProvider:
    """
    Basis-Klasse für alle Media-Provider (Netflix, YouTube, Spotify, etc.).

    Jeder Provider muss matches() und extract_info() implementieren.
    Optional können get_browser_url() und get_deep_link() überschrieben werden.

    Attributes:
        name: Anzeigename des Providers (z.B. "Netflix", "YouTube")
        source: Interne Quelle-ID für die Datenbank (z.B. "netflix", "youtube")
    """
    name = "base"
    source = "unknown"

    def matches(self, source_string: str) -> bool:
        """
        Prüft, ob der source_string zu diesem Provider gehört.

        Args:
            source_string: URL, Fenstertitel oder Dateipfad

        Returns:
            True wenn der Provider zuständig ist, sonst False
        """
        raise NotImplementedError

    def extract_info(self, source_string: str) -> dict:
        """
        Extrahiert Medien-Informationen aus dem source_string.

        Args:
            source_string: URL, Fenstertitel oder Dateipfad

        Returns:
            Dict mit keys: title, type, source, provider_id, has_real_id
            Optional: description, thumbnail_url, artist, album, channel, etc.
        """
        raise NotImplementedError

    def get_browser_url(self, provider_id: str) -> str | None:
        """
        Generiert Browser-URL aus provider_id (falls möglich).

        Args:
            provider_id: Eindeutige ID des Mediums beim Provider

        Returns:
            URL String oder None wenn nicht unterstützt
        """
        return None

    def get_deep_link(self, provider_id: str) -> str | None:
        """
        Generiert App Deep-Link aus provider_id (falls möglich).

        Args:
            provider_id: Eindeutige ID des Mediums beim Provider

        Returns:
            Deep-Link String oder None wenn nicht unterstützt
        """
        return None

    def _build_fallback_result(self, source_string: str, clean_phrases: list, default_type: str, overview_names: list = None) -> dict | None:
        """
        Helper für title-basierte Erkennung (Fallback wenn keine URL-ID).

        Args:
            source_string: Fenstertitel
            clean_phrases: Liste von Phrasen die entfernt werden sollen (z.B. [" - Netflix"])
            default_type: Medientyp (z.B. "movie", "music", "clip")
            overview_names: Namen die zu "[Provider] Übersicht" werden (optional)

        Returns:
            Dict mit Medien-Daten oder None
        """
        title = clean_window_title(source_string, clean_phrases)
        if not title:
            return None

        # Übersicht-Check
        if overview_names and title in overview_names:
            title = f"{self.name} Übersicht"

        return {
            "title": title,
            "type": default_type,
            "source": self.source,
            "provider_id": title,
            "description": "Automatisch erkannt (Browser)",
            "has_real_id": False
        }

# ============================================================
# Helper: Titel bereinigen
# ============================================================
def clean_window_title(title, remove_phrases):
    """
    Bereinigt Fenstertitel von Browser-Suffixen und Metadaten.

    Entfernt:
    - Provider-spezifische Suffixe (z.B. " - Netflix")
    - Browser-Namen (Edge, Chrome, Firefox)
    - Multi-Tab-Indikatoren ("und X weitere Seiten")
    - MediaBrain eigene Fenster (verhindert Selbst-Erkennung)

    Args:
        title: Roher Fenstertitel
        remove_phrases: Liste von Provider-spezifischen Phrasen zum Entfernen

    Returns:
        str: Bereinigter Titel oder None wenn MediaBrain-Fenster
    """
    # --- WICHTIG: Eigene App ignorieren ---
    if "MediaBrain" in title:
        return None
    # --------------------------------------

    # "und X weitere Seiten" entfernen
    title = re.sub(r" und \d+ weitere Seiten", "", title)

    # Browser-Müll entfernen (alles ab dem Trennzeichen)
    for phrase in remove_phrases:
        if phrase in title:
            title = title.split(phrase)[0]

    # Generische Browser-Endungen kappen
    for browser in [" - Persönlich", " - Microsoft​ Edge", " - Google Chrome", " - Mozilla Firefox"]:
        title = title.split(browser)[0]

    return title.strip()

# ============================================================
# 1. Netflix
# ============================================================
class NetflixProvider(BaseProvider):
    """
    Netflix Media Provider.

    Erkennt Netflix-Inhalte via:
    - URL: netflix.com/watch/{id}
    - Fenstertitel: "Titel - Netflix"

    Verwendet Fallback-Logik wenn keine URL-ID gefunden wird.
    """
    name = "Netflix"
    source = "netflix"
    regex = re.compile(r"netflix\.com/watch/(\d+)")

    def matches(self, source_string: str) -> bool:
        return bool(self.regex.search(source_string)) or ("Netflix" in source_string and "Netflix Party" not in source_string)

    def extract_info(self, source_string: str) -> dict:
        match = self.regex.search(source_string)
        if match:
            return {
                "title": f"Netflix Inhalt {match.group(1)}",
                "type": "movie",
                "source": self.source,
                "provider_id": match.group(1),
                "has_real_id": True
            }

        # Fallback: Title-basierte Erkennung
        return self._build_fallback_result(
            source_string,
            clean_phrases=[" - Netflix", " | Netflix"],
            default_type="movie",
            overview_names=["Netflix"]
        )

# ============================================================
# 2. YouTube
# ============================================================
class YouTubeProvider(BaseProvider):
    """
    YouTube Media Provider.

    Erkennt YouTube-Videos via:
    - URL: youtube.com/watch?v={video_id}
    - Fenstertitel: "Titel - YouTube"

    Erstellt automatisch Thumbnail-URL aus Video-ID.
    """
    name = "YouTube"
    source = "youtube"
    regex = re.compile(r"youtube\.com/watch\?v=([A-Za-z0-9_-]+)")

    def matches(self, source_string: str) -> bool:
        return bool(self.regex.search(source_string)) or ("YouTube" in source_string)

    def extract_info(self, source_string: str) -> dict:
        match = self.regex.search(source_string)
        if match:
            pid = match.group(1)
            return {
                "title": f"YouTube Video {pid}",
                "type": "clip",
                "source": self.source,
                "provider_id": pid,
                "thumbnail_url": f"https://img.youtube.com/vi/{pid}/0.jpg",
                "has_real_id": True
            }

        # Fallback: Title-basierte Erkennung
        return self._build_fallback_result(
            source_string,
            clean_phrases=[" - YouTube"],
            default_type="clip"
        )

# ============================================================
# 3. Spotify
# ============================================================
class SpotifyProvider(BaseProvider):
    """
    Spotify Media Provider.

    Erkennt Spotify-Inhalte via:
    - URL: open.spotify.com/{track|album|playlist}/{id}
    - Fenstertitel: "Titel - Spotify"

    Unterstützt Tracks, Alben und Playlists.
    """
    name = "Spotify"
    source = "spotify"
    regex = re.compile(r"open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)")
    
    def matches(self, s): 
        return "Spotify" in s or bool(self.regex.search(s))
    
    def extract_info(self, s):
        match = self.regex.search(s)
        if match:
            content_type = match.group(1)
            content_id = match.group(2)
            return {
                "title": f"Spotify {content_type.title()} {content_id[:8]}",
                "type": "music",
                "source": self.source,
                "provider_id": content_id,
                "has_real_id": True
            }

        # Fallback: Title-basierte Erkennung
        return self._build_fallback_result(
            s,
            clean_phrases=[" - Spotify", " | Spotify"],
            default_type="music"
        )

# ============================================================
# 4. Disney+ (NEU)
# ============================================================
class DisneyPlusProvider(BaseProvider):
    """
    Disney+ Media Provider.

    Erkennt Disney+-Inhalte via:
    - URL: disneyplus.com/video/{id}
    - Fenstertitel: "Titel - Disney+"
    """
    name = "Disney+"
    source = "disney"
    regex = re.compile(r"disneyplus\.com/video/([a-zA-Z0-9-]+)")

    def matches(self, source_string: str) -> bool:
        return (
            bool(self.regex.search(source_string)) or 
            "Disney+" in source_string or 
            "disneyplus" in source_string.lower()
        )

    def extract_info(self, source_string: str) -> dict:
        match = self.regex.search(source_string)
        if match:
            video_id = match.group(1)
            return {
                "title": f"Disney+ Video {video_id[:12]}",
                "type": "movie",
                "source": self.source,
                "provider_id": video_id,
                "has_real_id": True
            }

        # Fallback: Title-basierte Erkennung
        return self._build_fallback_result(
            source_string,
            clean_phrases=[" - Disney+", " | Disney+", "Disney+ |"],
            default_type="movie",
            overview_names=["Disney+", "Disney Plus"]
        )

# ============================================================
# 5. Amazon Prime Video (NEU)
# ============================================================
class AmazonPrimeProvider(BaseProvider):
    """
    Amazon Prime Video Media Provider.

    Erkennt Prime-Inhalte via:
    - URL: primevideo.com/detail/{id}
    - URL: amazon.{tld}/gp/video/detail/{id}
    - Fenstertitel: "Titel - Prime Video"
    """
    name = "Amazon Prime"
    source = "prime"
    regex = re.compile(r"primevideo\.com/detail/([a-zA-Z0-9]+)")
    regex_watch = re.compile(r"amazon\.[a-z]+/gp/video/detail/([a-zA-Z0-9]+)")

    def matches(self, source_string: str) -> bool:
        return (
            bool(self.regex.search(source_string)) or
            bool(self.regex_watch.search(source_string)) or
            "Prime Video" in source_string or
            "primevideo" in source_string.lower()
        )

    def extract_info(self, source_string: str) -> dict:
        # URL-basierte Erkennung
        match = self.regex.search(source_string) or self.regex_watch.search(source_string)
        if match:
            video_id = match.group(1)
            return {
                "title": f"Prime Video {video_id}",
                "type": "movie",
                "source": self.source,
                "provider_id": video_id,
                "has_real_id": True
            }
        
        title = clean_window_title(source_string, [" - Prime Video", " | Prime Video", "Prime Video -"])
        if not title:
            return None

        if title in ["Prime Video", "Amazon Prime Video"]:
            title = "Prime Video Übersicht"
            
        return {
            "title": title,
            "type": "movie",
            "source": self.source,
            "provider_id": title,
            "description": "Automatisch erkannt (Browser)",
            "has_real_id": False
        }

# ============================================================
# 6. Apple TV+ (NEU)
# ============================================================
class AppleTVProvider(BaseProvider):
    """
    Apple TV+ Media Provider.

    Erkennt Apple TV+-Inhalte via:
    - URL: tv.apple.com/{lang}/{movie|show|episode}/{title}/{id}
    - Fenstertitel: "Titel - Apple TV+"
    """
    name = "Apple TV+"
    source = "appletv"
    regex = re.compile(r"tv\.apple\.com/[a-z]+/(?:movie|show|episode)/[^/]+/([a-z0-9]+)")

    def matches(self, source_string: str) -> bool:
        return (
            bool(self.regex.search(source_string)) or
            "Apple TV" in source_string or
            "tv.apple.com" in source_string.lower()
        )

    def extract_info(self, source_string: str) -> dict:
        match = self.regex.search(source_string)
        if match:
            content_id = match.group(1)
            return {
                "title": f"Apple TV+ {content_id}",
                "type": "movie",
                "source": self.source,
                "provider_id": content_id,
                "has_real_id": True
            }
        
        title = clean_window_title(source_string, [" - Apple TV+", " | Apple TV+", "Apple TV+ -"])
        if not title:
            return None

        if title in ["Apple TV+", "Apple TV"]:
            title = "Apple TV+ Übersicht"
            
        return {
            "title": title,
            "type": "movie",
            "source": self.source,
            "provider_id": title,
            "description": "Automatisch erkannt (Browser)",
            "has_real_id": False
        }

# ============================================================
# 7. Twitch (NEU - Bonus)
# ============================================================
class TwitchProvider(BaseProvider):
    """
    Twitch Media Provider.

    Erkennt Twitch-Streams via:
    - URL: twitch.tv/{channel}
    - Fenstertitel: "Titel - Twitch"

    Filtert System-Seiten wie /directory, /settings, /videos.
    """
    name = "Twitch"
    source = "twitch"
    regex = re.compile(r"twitch\.tv/([a-zA-Z0-9_]+)")

    def matches(self, source_string: str) -> bool:
        return bool(self.regex.search(source_string)) or "Twitch" in source_string

    def extract_info(self, source_string: str) -> dict:
        match = self.regex.search(source_string)
        if match:
            channel = match.group(1)
            if channel.lower() not in ["directory", "settings", "videos"]:
                return {
                    "title": f"Twitch: {channel}",
                    "type": "clip",
                    "source": self.source,
                    "provider_id": channel,
                    "channel": channel,
                    "has_real_id": True
                }
        
        title = clean_window_title(source_string, [" - Twitch"])
        if not title:
            return None
            
        return {
            "title": title,
            "type": "clip",
            "source": self.source,
            "provider_id": title,
            "description": "Automatisch erkannt (Browser)",
            "has_real_id": False
        }

# ============================================================
# 8. LocalProvider
# ============================================================
class LocalProvider(BaseProvider):
    """
    Local File Media Provider.

    Erkennt lokale Dateien via:
    - Dateipfad (existiert und ist Datei)

    Unterstützte Formate:
    - Video: mp4, mkv, avi, mov, wmv, webm
    - Audio: mp3, flac, wav, m4a, aac, ogg
    - Dokumente: pdf, epub
    - Hörbücher: m4b
    """
    name = "Local"
    source = "local"
    SUPPORTED = {
        # Video
        ".mp4": "movie", ".mkv": "movie", ".avi": "movie",
        ".mov": "movie", ".wmv": "movie", ".webm": "clip",
        # Audio
        ".mp3": "music", ".flac": "music", ".wav": "music",
        ".m4a": "music", ".aac": "music", ".ogg": "music",
        # Dokumente
        ".pdf": "document", ".epub": "document",
        # Podcast/Hörbuch
        ".m4b": "audiobook"
    }

    def matches(self, s):
        try:
            return Path(s).exists() and Path(s).is_file()
        except (OSError, ValueError):
            return False

    def extract_info(self, s):
        path = Path(s)
        t = self.SUPPORTED.get(path.suffix.lower(), "file")
        return {
            "title": path.stem,
            "type": t,
            "source": "local",
            "provider_id": str(path.resolve()),
            "is_local_file": True,
            "local_path": str(path.resolve()),
            "has_real_id": True
        }

# ============================================================
# Registry - Erweitert
# ============================================================
class ProviderRegistry:
    """
    Zentrale Registry aller Media-Provider.

    Verwendet Chain-of-Responsibility Pattern:
    Jeder Provider wird nacheinander geprüft bis ein Match gefunden wird.

    Reihenfolge ist wichtig: Spezifischere Provider (Netflix, Disney+)
    vor generischeren (Local).
    """
    providers = [
        NetflixProvider(),
        DisneyPlusProvider(),      # NEU
        AmazonPrimeProvider(),     # NEU
        AppleTVProvider(),         # NEU
        YouTubeProvider(),
        TwitchProvider(),          # NEU
        SpotifyProvider(),
        LocalProvider()
    ]

    @classmethod
    def identify(cls, source_string: str) -> dict | None:
        """Identifiziert Medienquelle aus URL oder Fenstertitel."""
        for p in cls.providers:
            if p.matches(source_string):
                result = p.extract_info(source_string)
                if result:
                    print(f"[Registry] Treffer! Provider: {p.name} -> {source_string[:40]}...")
                    return result
        return None
    
    @classmethod
    def get_provider_names(cls) -> list:
        """Gibt Liste aller Provider-Namen zurück."""
        return [p.name for p in cls.providers]
    
    @classmethod
    def get_provider_by_source(cls, source: str):
        """Findet Provider anhand source-ID."""
        for p in cls.providers:
            if p.source == source:
                return p
        return None
