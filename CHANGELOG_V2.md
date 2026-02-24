# MediaBrain V2.0 - Neue Features

## Übersicht der Erweiterungen

### 1. Metadata V2 (metadata_v2.py)
Erweiterte Metadaten-Abfrage mit Multi-Provider-Support:

**APIs:**
- TMDb (The Movie Database) - Filme & Serien
- OMDb (Open Movie Database) - Fallback für Filme
- MusicBrainz - Musik (kein API-Key nötig)

**Verwendung:**
```python
from metadata_v2 import MetadataFetcher

fetcher = MetadataFetcher()

# Film-Metadaten
movie = fetcher.fetch_movie("Inception", year=2010)
# Returns: title, year, overview, poster_url, backdrop_url, rating, genres

# Serien-Metadaten
series = fetcher.fetch_series("Breaking Bad")

# Musik-Metadaten
music = fetcher.fetch_music("Bohemian Rhapsody", artist="Queen")

# Automatische Erkennung
auto = fetcher.auto_fetch("Stranger Things", media_type="series")
```

**API-Keys konfigurieren:**
1. Umgebungsvariablen: `TMDB_API_KEY`, `OMDB_API_KEY`
2. Oder in `~/.mediabrain/settings.json`:
```json
{
    "api_keys": {
        "tmdb": "your-tmdb-key",
        "omdb": "your-omdb-key"
    }
}
```

---

### 2. Erweiterte Provider (providers.py)
Neue Streaming-Dienste hinzugefügt:

| Provider | Source-ID | URL-Pattern |
|----------|-----------|-------------|
| Netflix | netflix | netflix.com/watch/* |
| **Disney+** | disney | disneyplus.com/video/* |
| **Amazon Prime** | prime | primevideo.com/detail/* |
| **Apple TV+** | appletv | tv.apple.com/*/* |
| YouTube | youtube | youtube.com/watch?v=* |
| **Twitch** | twitch | twitch.tv/* |
| Spotify | spotify | open.spotify.com/* |
| Lokal | local | Dateipfade |

**Neue Dateiformate (LocalProvider):**
- Video: .mp4, .mkv, .avi, .mov, .wmv, .webm
- Audio: .mp3, .flac, .wav, .m4a, .aac, .ogg
- Hörbücher: .m4b
- Dokumente: .pdf, .epub

---

### 3. Erweiterte Suche (search_advanced.py)
Leistungsfähige Suchfunktion mit Filtern:

**Filter-Optionen:**
- Medientyp (Filme, Serien, Musik, etc.)
- Provider (Netflix, Disney+, YouTube, etc.)
- Zeitraum (Heute, 7 Tage, 30 Tage, etc.)
- Nur Favoriten
- Blacklist ein/ausblenden
- Nur lokale Dateien

**Sortierung:**
- Zuletzt geöffnet
- Titel A-Z / Z-A
- Hinzugefügt (neu/alt)
- Bewertung

**Suchprofile:**
Häufig genutzte Suchen können gespeichert werden.

**Verwendung in GUI:**
```python
from search_advanced import AdvancedSearchBar, SearchEngine

# In MainWindow:
self.search_bar = AdvancedSearchBar()
self.search_bar.search_triggered.connect(self.on_search)

def on_search(self, criteria):
    engine = SearchEngine(self.db)
    results = engine.search(criteria)
    self.display_results(results)
```

---

## Integration

Die neuen Module sind rückwärtskompatibel:
- `metadata_v2.py` enthält weiterhin `fetch_metadata(url)` für OpenGraph
- `providers.py` erweitert die bestehende Registry
- `search_advanced.py` ist ein optionales Add-on zur GUI

## Nächste Schritte

1. GUI-Integration der AdvancedSearchBar
2. Metadaten-Button in MediaItemWidget
3. Provider-Icons in der Anzeige
4. Einstellungs-Dialog für API-Keys
