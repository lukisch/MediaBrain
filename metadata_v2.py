"""
metadata_v2.py
Erweiterte Metadaten-Fetch-Funktionen für MediaBrain.
- OpenGraph für URLs
- TMDb für Filme/Serien
- OMDb für Filme (Fallback)
- MusicBrainz für Musik (Basis)

Version: 2.0
"""
import requests
import re
import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

# Optionale Imports
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# ============================================================
# Konfiguration - API Keys werden aus Umgebung oder Config geladen
# ============================================================

CONFIG_PATH = Path(__file__).parent / "settings.json"

def get_api_key(service):
    """Holt API-Key aus settings.json oder Umgebungsvariable."""
    # 1. Umgebungsvariable
    env_key = os.environ.get(f"{service.upper()}_API_KEY")
    if env_key:
        return env_key
    
    # 2. settings.json
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("api_keys", {}).get(service, "")
        except:
            pass
    
    return ""

# ============================================================
# 1. OpenGraph Metadata (wie bisher)
# ============================================================

def fetch_opengraph(url):
    """Holt OpenGraph-Metadaten von einer URL."""
    if not HAS_BS4:
        return None
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        data = {}

        # Titel
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"]
            title = title.replace(" - YouTube", "").replace(" | Netflix", "")
            data["title"] = title
        else:
            data["title"] = soup.title.string if soup.title else "Unbekannter Titel"

        # Beschreibung
        og_desc = soup.find("meta", property="og:description")
        if og_desc:
            data["description"] = og_desc.get("content")

        # Thumbnail
        og_image = soup.find("meta", property="og:image")
        if og_image:
            data["thumbnail_url"] = og_image.get("content")

        return data

    except Exception as e:
        print(f"[Metadata] OpenGraph Fehler bei {url}: {e}")
        return None

# ============================================================
# 2. TMDb (The Movie Database)
# ============================================================

class TMDbFetcher:
    """Holt Metadaten von The Movie Database (TMDb)."""
    
    BASE_URL = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or get_api_key("tmdb")
        
    def is_available(self):
        """Prüft ob API-Key vorhanden ist."""
        return bool(self.api_key)
    
    def search_movie(self, title, year=None):
        """Sucht nach einem Film."""
        if not self.is_available():
            return None
            
        try:
            params = {
                "api_key": self.api_key,
                "query": title,
                "language": "de-DE"
            }
            if year:
                params["year"] = year
                
            response = requests.get(
                f"{self.BASE_URL}/search/movie",
                params=params,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    return data["results"][0]  # Bester Treffer
                    
        except Exception as e:
            print(f"[TMDb] Suche fehlgeschlagen: {e}")
        
        return None
    
    def search_tv(self, title, year=None):
        """Sucht nach einer Serie."""
        if not self.is_available():
            return None
            
        try:
            params = {
                "api_key": self.api_key,
                "query": title,
                "language": "de-DE"
            }
            if year:
                params["first_air_date_year"] = year
                
            response = requests.get(
                f"{self.BASE_URL}/search/tv",
                params=params,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    return data["results"][0]
                    
        except Exception as e:
            print(f"[TMDb] TV-Suche fehlgeschlagen: {e}")
        
        return None
    
    def get_movie_details(self, movie_id):
        """Holt detaillierte Film-Informationen."""
        if not self.is_available():
            return None
            
        try:
            response = requests.get(
                f"{self.BASE_URL}/movie/{movie_id}",
                params={"api_key": self.api_key, "language": "de-DE"},
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            print(f"[TMDb] Details fehlgeschlagen: {e}")
        
        return None
    
    def format_result(self, tmdb_data, media_type="movie"):
        """Formatiert TMDb-Ergebnis für MediaBrain."""
        if not tmdb_data:
            return None
            
        result = {
            "title": tmdb_data.get("title") or tmdb_data.get("name"),
            "description": tmdb_data.get("overview"),
            "tmdb_id": tmdb_data.get("id"),
            "type": media_type,
            "source": "tmdb"
        }
        
        # Poster
        poster = tmdb_data.get("poster_path")
        if poster:
            result["thumbnail_url"] = f"{self.IMAGE_BASE}/w500{poster}"
        
        # Backdrop
        backdrop = tmdb_data.get("backdrop_path")
        if backdrop:
            result["backdrop_url"] = f"{self.IMAGE_BASE}/original{backdrop}"
        
        # Rating
        result["rating"] = tmdb_data.get("vote_average")
        
        # Release-Jahr
        release = tmdb_data.get("release_date") or tmdb_data.get("first_air_date")
        if release:
            result["year"] = release[:4]
        
        # Genres
        genres = tmdb_data.get("genres", [])
        if genres:
            result["genres"] = [g["name"] for g in genres]
        
        return result

# ============================================================
# 3. OMDb (Open Movie Database) - Fallback
# ============================================================

class OMDbFetcher:
    """Holt Metadaten von OMDb (IMDb-basiert)."""
    
    BASE_URL = "http://www.omdbapi.com/"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or get_api_key("omdb")

    def is_available(self):
        """Prüft ob API-Key vorhanden ist."""
        return bool(self.api_key)
    
    def search(self, title, year=None, media_type=None):
        """Sucht nach einem Film/Serie."""
        if not self.is_available():
            return None
            
        try:
            params = {
                "apikey": self.api_key,
                "t": title,
                "plot": "short"
            }
            if year:
                params["y"] = year
            if media_type:
                params["type"] = media_type  # movie, series, episode
                
            response = requests.get(self.BASE_URL, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("Response") == "True":
                    return data
                    
        except Exception as e:
            print(f"[OMDb] Suche fehlgeschlagen: {e}")
        
        return None
    
    def format_result(self, omdb_data):
        """Formatiert OMDb-Ergebnis für MediaBrain."""
        if not omdb_data:
            return None
            
        result = {
            "title": omdb_data.get("Title"),
            "description": omdb_data.get("Plot"),
            "imdb_id": omdb_data.get("imdbID"),
            "year": omdb_data.get("Year"),
            "source": "omdb"
        }
        
        # Typ
        media_type = omdb_data.get("Type", "movie")
        result["type"] = "series" if media_type == "series" else "movie"
        
        # Poster
        poster = omdb_data.get("Poster")
        if poster and poster != "N/A":
            result["thumbnail_url"] = poster
        
        # Rating
        rating = omdb_data.get("imdbRating")
        if rating and rating != "N/A":
            result["rating"] = float(rating)
        
        # Genres
        genres = omdb_data.get("Genre")
        if genres and genres != "N/A":
            result["genres"] = [g.strip() for g in genres.split(",")]
        
        # Weitere Infos
        result["director"] = omdb_data.get("Director") if omdb_data.get("Director") != "N/A" else None
        result["actors"] = omdb_data.get("Actors") if omdb_data.get("Actors") != "N/A" else None
        result["runtime"] = omdb_data.get("Runtime") if omdb_data.get("Runtime") != "N/A" else None
        
        return result

# ============================================================
# 4. MusicBrainz (Basis-Implementation)
# ============================================================

class MusicBrainzFetcher:
    """Holt Metadaten von MusicBrainz (keine API-Key nötig)."""
    
    BASE_URL = "https://musicbrainz.org/ws/2"
    COVER_URL = "https://coverartarchive.org"
    
    def search_artist(self, name):
        """Sucht nach einem Künstler."""
        try:
            response = requests.get(
                f"{self.BASE_URL}/artist",
                params={"query": name, "fmt": "json", "limit": 1},
                headers={"User-Agent": "MediaBrain/2.0"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("artists"):
                    return data["artists"][0]
                    
        except Exception as e:
            print(f"[MusicBrainz] Suche fehlgeschlagen: {e}")
        
        return None
    
    def search_release(self, title, artist=None):
        """Sucht nach einem Album/Release."""
        try:
            query = f'release:"{title}"'
            if artist:
                query += f' AND artist:"{artist}"'
                
            response = requests.get(
                f"{self.BASE_URL}/release",
                params={"query": query, "fmt": "json", "limit": 1},
                headers={"User-Agent": "MediaBrain/2.0"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("releases"):
                    return data["releases"][0]
                    
        except Exception as e:
            print(f"[MusicBrainz] Release-Suche fehlgeschlagen: {e}")
        
        return None
    
    def get_cover_art(self, release_id):
        """Holt Cover-Art URL für ein Release."""
        try:
            response = requests.get(
                f"{self.COVER_URL}/release/{release_id}",
                headers={"User-Agent": "MediaBrain/2.0"},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                images = data.get("images", [])
                if images:
                    return images[0].get("image")
                    
        except:
            pass
        
        return None

# ============================================================
# 5. Metadata Cache (SQLite-basiert)
# ============================================================

class MetadataCache:
    """SQLite-basierter Cache fuer Metadaten-API-Antworten."""

    DEFAULT_TTL_DAYS = 30

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent / "metadata_cache.db"
        self.db_path = str(db_path)
        self._setup()

    def _setup(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metadata_cache (
                cache_key TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    @staticmethod
    def _make_key(source, query, media_type=None, year=None, artist=None):
        parts = [source, query, media_type or "", year or "", artist or ""]
        raw = "|".join(str(p).lower().strip() for p in parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, source, query, media_type=None, year=None, artist=None):
        key = self._make_key(source, query, media_type, year, artist)
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT result_json, expires_at FROM metadata_cache WHERE cache_key = ?",
            (key,)
        ).fetchone()
        conn.close()

        if row is None:
            return None

        if datetime.fromisoformat(row[1]) < datetime.now():
            self.delete(key)
            return None

        return json.loads(row[0])

    def put(self, source, query, result, media_type=None, year=None, artist=None, ttl_days=None):
        if result is None:
            return
        key = self._make_key(source, query, media_type, year, artist)
        now = datetime.now()
        expires = now + timedelta(days=ttl_days or self.DEFAULT_TTL_DAYS)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO metadata_cache (cache_key, result_json, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (key, json.dumps(result, ensure_ascii=False), now.isoformat(), expires.isoformat())
        )
        conn.commit()
        conn.close()

    def delete(self, key):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM metadata_cache WHERE cache_key = ?", (key,))
        conn.commit()
        conn.close()

    def clear_expired(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM metadata_cache WHERE expires_at < ?", (datetime.now().isoformat(),))
        conn.commit()
        conn.close()


# ============================================================
# 6. Unified Metadata Fetcher
# ============================================================

class MetadataFetcher:
    """
    Einheitlicher Metadaten-Fetcher für MediaBrain.
    Kombiniert alle Quellen mit Fallback-Logik.
    """
    
    def __init__(self, cache_enabled=True):
        self.tmdb = TMDbFetcher()
        self.omdb = OMDbFetcher()
        self.musicbrainz = MusicBrainzFetcher()
        self.cache = MetadataCache() if cache_enabled else None

    def _cache_get(self, source, query, media_type=None, year=None, artist=None):
        """
        Holt Metadaten aus Cache (falls aktiviert).

        Args:
            source: Quelle (movie, series, music)
            query: Suchbegriff
            media_type: Medientyp (optional)
            year: Jahr (optional)
            artist: Künstler für Musik (optional)

        Returns:
            Gecachte Metadaten oder None
        """
        if self.cache:
            return self.cache.get(source, query, media_type, year, artist)
        return None

    def _cache_put(self, source, query, result, media_type=None, year=None, artist=None):
        """
        Speichert Metadaten in Cache (falls aktiviert und result nicht None).

        Args:
            source: Quelle (movie, series, music)
            query: Suchbegriff
            result: Metadaten-Dict zum Cachen
            media_type: Medientyp (optional)
            year: Jahr (optional)
            artist: Künstler für Musik (optional)
        """
        if self.cache and result:
            self.cache.put(source, query, result, media_type, year, artist)

    def fetch_movie(self, title, year=None):
        """Holt Film-Metadaten (Cache → TMDb → OMDb Fallback)."""
        cached = self._cache_get("movie", title, "movie", str(year) if year else None)
        if cached:
            return cached

        result = None
        # 1. TMDb versuchen
        if self.tmdb.is_available():
            raw = self.tmdb.search_movie(title, year)
            if raw:
                details = self.tmdb.get_movie_details(raw["id"])
                if details:
                    result = self.tmdb.format_result(details, "movie")
                else:
                    result = self.tmdb.format_result(raw, "movie")

        # 2. OMDb Fallback
        if result is None and self.omdb.is_available():
            raw = self.omdb.search(title, year, "movie")
            if raw:
                result = self.omdb.format_result(raw)

        self._cache_put("movie", title, result, "movie", str(year) if year else None)
        return result

    def fetch_series(self, title, year=None):
        """Holt Serien-Metadaten (Cache → TMDb → OMDb Fallback)."""
        cached = self._cache_get("series", title, "series", str(year) if year else None)
        if cached:
            return cached

        result = None
        # 1. TMDb
        if self.tmdb.is_available():
            raw = self.tmdb.search_tv(title, year)
            if raw:
                result = self.tmdb.format_result(raw, "series")

        # 2. OMDb Fallback
        if result is None and self.omdb.is_available():
            raw = self.omdb.search(title, year, "series")
            if raw:
                result = self.omdb.format_result(raw)

        self._cache_put("series", title, result, "series", str(year) if year else None)
        return result

    def fetch_music(self, title, artist=None):
        """Holt Musik-Metadaten (Cache → MusicBrainz)."""
        cached = self._cache_get("music", title, "music", artist=artist)
        if cached:
            return cached

        raw = self.musicbrainz.search_release(title, artist)
        result = None
        if raw:
            release_id = raw.get("id")
            result = {
                "title": raw.get("title"),
                "artist": raw.get("artist-credit", [{}])[0].get("name"),
                "year": raw.get("date", "")[:4] if raw.get("date") else None,
                "thumbnail_url": self.musicbrainz.get_cover_art(release_id) if release_id else None,
                "type": "music",
                "source": "musicbrainz"
            }

        self._cache_put("music", title, result, "music", artist=artist)
        return result

    def auto_fetch(self, title, media_type="movie", year=None, artist=None):
        """
        Automatischer Fetch basierend auf Medientyp.
        
        Args:
            title: Titel des Mediums
            media_type: movie, series, music, clip
            year: Erscheinungsjahr (optional)
            artist: Künstler für Musik (optional)
        """
        if media_type in ["movie", "film"]:
            return self.fetch_movie(title, year)
        elif media_type in ["series", "show", "tv"]:
            return self.fetch_series(title, year)
        elif media_type in ["music", "song", "album"]:
            return self.fetch_music(title, artist)
        else:
            # Versuche Film zuerst
            result = self.fetch_movie(title, year)
            if result:
                return result
            return self.fetch_series(title, year)
    
    def get_status(self):
        """Gibt Status der API-Verbindungen zurück."""
        return {
            "tmdb": self.tmdb.is_available(),
            "omdb": self.omdb.is_available(),
            "musicbrainz": True  # Keine API-Key nötig
        }

# ============================================================
# Legacy-Kompatibilität
# ============================================================

def fetch_metadata(url):
    """Legacy-Funktion für Abwärtskompatibilität."""
    return fetch_opengraph(url)

# ============================================================
# Test
# ============================================================

if __name__ == "__main__":
    fetcher = MetadataFetcher()
    
    print("API Status:", fetcher.get_status())
    
    # Test Film
    print("\n--- Film-Test ---")
    result = fetcher.fetch_movie("Inception")
    if result:
        print(f"Titel: {result.get('title')}")
        print(f"Jahr: {result.get('year')}")
        print(f"Rating: {result.get('rating')}")
    else:
        print("Keine API-Keys konfiguriert oder keine Ergebnisse")
    
    # Test MusicBrainz (kein API-Key nötig)
    print("\n--- Musik-Test ---")
    result = fetcher.fetch_music("Abbey Road", "The Beatles")
    if result:
        print(f"Album: {result.get('title')}")
        print(f"Artist: {result.get('artist')}")
