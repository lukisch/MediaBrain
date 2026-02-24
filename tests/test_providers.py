"""
test_providers.py
Unit Tests für Provider-Klassen

Testet:
- URL-basierte Erkennung
- Fenstertitel-basierte Erkennung
- Korrekte Extraktion von provider_id
- Korrekte Typzuordnung
"""

import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from providers import (
    NetflixProvider,
    YouTubeProvider,
    SpotifyProvider,
    DisneyPlusProvider,
    AmazonPrimeProvider,
    AppleTVProvider,
    TwitchProvider,
    LocalProvider,
    ProviderRegistry,
    clean_window_title
)


class TestCleanWindowTitle(unittest.TestCase):
    """Test für clean_window_title Helper"""

    def test_removes_browser_suffix(self):
        """Browser-Suffixe werden entfernt"""
        result = clean_window_title("Netflix - Google Chrome", [" - Google Chrome"])
        self.assertEqual(result, "Netflix")

    def test_removes_netflix_phrase(self):
        """Netflix-spezifische Phrasen werden entfernt"""
        result = clean_window_title("Stranger Things - Netflix", [" - Netflix"])
        self.assertEqual(result, "Stranger Things")

    def test_ignores_mediabrain(self):
        """MediaBrain-Fenster werden ignoriert"""
        result = clean_window_title("MediaBrain - Dashboard", [])
        self.assertIsNone(result)

    def test_removes_multiple_tabs_phrase(self):
        """'und X weitere Seiten' wird entfernt"""
        result = clean_window_title("YouTube und 5 weitere Seiten - Chrome", [" - Chrome"])
        self.assertEqual(result, "YouTube")


class TestNetflixProvider(unittest.TestCase):
    """Tests für NetflixProvider"""

    def setUp(self):
        self.provider = NetflixProvider()

    def test_matches_url(self):
        """URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://www.netflix.com/watch/12345"))

    def test_matches_window_title(self):
        """Fenstertitel wird erkannt"""
        self.assertTrue(self.provider.matches("Stranger Things - Netflix"))

    def test_extract_from_url(self):
        """Extraktion aus URL"""
        result = self.provider.extract_info("https://www.netflix.com/watch/80057281")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "netflix")
        self.assertEqual(result["provider_id"], "80057281")
        self.assertTrue(result["has_real_id"])

    def test_extract_from_window_title(self):
        """Extraktion aus Fenstertitel"""
        result = self.provider.extract_info("Stranger Things - Netflix")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Stranger Things")
        self.assertEqual(result["source"], "netflix")
        self.assertFalse(result["has_real_id"])

    def test_netflix_overview(self):
        """Netflix Übersicht wird erkannt"""
        result = self.provider.extract_info("Netflix - Google Chrome")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Netflix Übersicht")


class TestYouTubeProvider(unittest.TestCase):
    """Tests für YouTubeProvider"""

    def setUp(self):
        self.provider = YouTubeProvider()

    def test_matches_url(self):
        """URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_extract_from_url(self):
        """Extraktion aus URL"""
        result = self.provider.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertIsNotNone(result)
        self.assertEqual(result["provider_id"], "dQw4w9WgXcQ")
        self.assertEqual(result["type"], "clip")
        self.assertTrue(result["has_real_id"])
        self.assertIn("thumbnail_url", result)

    def test_extract_from_window_title(self):
        """Extraktion aus Fenstertitel"""
        result = self.provider.extract_info("Rick Astley - Never Gonna Give You Up - YouTube")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Rick Astley - Never Gonna Give You Up")


class TestSpotifyProvider(unittest.TestCase):
    """Tests für SpotifyProvider"""

    def setUp(self):
        self.provider = SpotifyProvider()

    def test_matches_url_track(self):
        """Track-URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"))

    def test_matches_url_album(self):
        """Album-URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://open.spotify.com/album/6DEjYFkNZh67HP7R9PSZvv"))

    def test_extract_from_track_url(self):
        """Extraktion aus Track-URL"""
        result = self.provider.extract_info("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
        self.assertIsNotNone(result)
        self.assertEqual(result["provider_id"], "4uLU6hMCjMI75M1A2tKUQC")
        self.assertEqual(result["type"], "music")
        self.assertTrue(result["has_real_id"])

    def test_extract_from_window_title(self):
        """Extraktion aus Fenstertitel"""
        result = self.provider.extract_info("Never Gonna Give You Up - Spotify")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Never Gonna Give You Up")


class TestDisneyPlusProvider(unittest.TestCase):
    """Tests für DisneyPlusProvider"""

    def setUp(self):
        self.provider = DisneyPlusProvider()

    def test_matches_url(self):
        """URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://www.disneyplus.com/video/abc-123-def"))

    def test_extract_from_url(self):
        """Extraktion aus URL"""
        result = self.provider.extract_info("https://www.disneyplus.com/video/the-mandalorian-s01e01")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "disney")
        self.assertTrue(result["has_real_id"])


class TestAmazonPrimeProvider(unittest.TestCase):
    """Tests für AmazonPrimeProvider"""

    def setUp(self):
        self.provider = AmazonPrimeProvider()

    def test_matches_primevideo_url(self):
        """primevideo.com URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://www.primevideo.com/detail/B08WTXR123"))

    def test_matches_amazon_url(self):
        """amazon.de URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://www.amazon.de/gp/video/detail/B08WTXR123"))


class TestAppleTVProvider(unittest.TestCase):
    """Tests für AppleTVProvider"""

    def setUp(self):
        self.provider = AppleTVProvider()

    def test_matches_url(self):
        """URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://tv.apple.com/us/movie/test/umc12345"))


class TestTwitchProvider(unittest.TestCase):
    """Tests für TwitchProvider"""

    def setUp(self):
        self.provider = TwitchProvider()

    def test_matches_channel_url(self):
        """Channel-URL wird erkannt"""
        self.assertTrue(self.provider.matches("https://www.twitch.tv/ninja"))

    def test_extract_from_channel_url(self):
        """Extraktion aus Channel-URL"""
        result = self.provider.extract_info("https://www.twitch.tv/ninja")
        self.assertIsNotNone(result)
        self.assertEqual(result["provider_id"], "ninja")
        self.assertEqual(result["channel"], "ninja")
        self.assertEqual(result["type"], "clip")

    def test_ignores_directory_page(self):
        """Directory-Seiten werden ignoriert"""
        result = self.provider.extract_info("https://www.twitch.tv/directory")
        # Sollte None oder nur Title-basiert zurückgeben
        if result:
            self.assertNotEqual(result.get("provider_id"), "directory")


class TestLocalProvider(unittest.TestCase):
    """Tests für LocalProvider"""

    def setUp(self):
        self.provider = LocalProvider()

    def test_type_mapping_video(self):
        """Video-Dateitypen werden korrekt zugeordnet"""
        types = {".mp4": "movie", ".mkv": "movie", ".webm": "clip"}
        for ext, expected_type in types.items():
            self.assertEqual(self.provider.SUPPORTED[ext], expected_type)

    def test_type_mapping_audio(self):
        """Audio-Dateitypen werden korrekt zugeordnet"""
        types = {".mp3": "music", ".flac": "music", ".m4a": "music"}
        for ext, expected_type in types.items():
            self.assertEqual(self.provider.SUPPORTED[ext], expected_type)


class TestProviderRegistry(unittest.TestCase):
    """Tests für ProviderRegistry"""

    def test_identify_netflix_url(self):
        """Netflix-URL wird identifiziert"""
        result = ProviderRegistry.identify("https://www.netflix.com/watch/80057281")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "netflix")

    def test_identify_youtube_url(self):
        """YouTube-URL wird identifiziert"""
        result = ProviderRegistry.identify("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "youtube")

    def test_identify_spotify_url(self):
        """Spotify-URL wird identifiziert"""
        result = ProviderRegistry.identify("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "spotify")

    def test_get_provider_names(self):
        """Alle Provider-Namen werden zurückgegeben"""
        names = ProviderRegistry.get_provider_names()
        self.assertIn("Netflix", names)
        self.assertIn("YouTube", names)
        self.assertIn("Spotify", names)
        self.assertIn("Disney+", names)
        self.assertIn("Amazon Prime", names)
        self.assertIn("Apple TV+", names)
        self.assertIn("Twitch", names)
        self.assertIn("Local", names)

    def test_get_provider_by_source(self):
        """Provider kann anhand source gefunden werden"""
        netflix = ProviderRegistry.get_provider_by_source("netflix")
        self.assertIsNotNone(netflix)
        self.assertEqual(netflix.name, "Netflix")


if __name__ == "__main__":
    unittest.main()
