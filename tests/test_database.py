"""
test_database.py
Integration Tests für Database und MediaManager

Testet:
- Database CRUD Operations
- MediaManager add_or_update mit Validierung
- MediaManager list_by_type
- BlacklistManager Funktionalität
"""

import sys
from pathlib import Path

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from core import Database, MediaManager, MediaItem, BlacklistManager


class TestDatabase(unittest.TestCase):
    """Integration Tests für Database-Klasse"""

    def setUp(self):
        """Erstellt temporäre Test-Datenbank für jeden Test"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)

    def tearDown(self):
        """Räumt temporäre Datenbank auf"""
        self.db.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_database_initialization(self):
        """Datenbank wird korrekt initialisiert"""
        # Prüfe ob Tabelle existiert
        cursor = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='media_items'"
        )
        self.assertIsNotNone(cursor.fetchone())

    def test_database_indexes_created(self):
        """Alle Indizes werden erstellt"""
        cursor = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        # Prüfe wichtige Indizes
        self.assertIn("idx_media_last_opened", indexes)
        self.assertIn("idx_media_type", indexes)
        self.assertIn("idx_media_favorite", indexes)
        self.assertIn("idx_media_blacklist", indexes)
        self.assertIn("idx_media_type_blacklist", indexes)  # Composite Index

    def test_execute_query(self):
        """execute() führt INSERT aus"""
        self.db.execute(
            "INSERT INTO media_items (title, type, source, provider_id) VALUES (?, ?, ?, ?)",
            ("Test Movie", "movie", "netflix", "12345")
        )
        rows = self.db.fetchall("SELECT * FROM media_items WHERE title = ?", ("Test Movie",))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Test Movie")

    def test_fetchone_returns_single_row(self):
        """fetchone() gibt einzelne Row zurück"""
        self.db.execute(
            "INSERT INTO media_items (title, type, source, provider_id) VALUES (?, ?, ?, ?)",
            ("Single Row Test", "movie", "netflix", "99999")
        )
        row = self.db.fetchone("SELECT * FROM media_items WHERE provider_id = ?", ("99999",))
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Single Row Test")

    def test_fetchall_returns_multiple_rows(self):
        """fetchall() gibt mehrere Rows zurück"""
        # Mehrere Einträge einfügen
        for i in range(5):
            self.db.execute(
                "INSERT INTO media_items (title, type, source, provider_id) VALUES (?, ?, ?, ?)",
                (f"Movie {i}", "movie", "netflix", f"id_{i}")
            )

        rows = self.db.fetchall("SELECT * FROM media_items WHERE type = ?", ("movie",))
        self.assertEqual(len(rows), 5)


class TestMediaManager(unittest.TestCase):
    """Integration Tests für MediaManager"""

    def setUp(self):
        """Erstellt temporäre Test-Datenbank für jeden Test"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.manager = MediaManager(self.db)

    def tearDown(self):
        """Räumt temporäre Datenbank auf"""
        self.db.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_add_or_update_valid_data(self):
        """Valide Daten werden eingefügt"""
        data = {
            "title": "Test Movie",
            "type": "movie",
            "source": "netflix",
            "provider_id": "12345",
            "has_real_id": True
        }
        self.manager.add_or_update(data)

        # Prüfe ob Eintrag existiert
        item = self.manager.get_by_provider("12345", "netflix")
        self.assertIsNotNone(item)
        self.assertEqual(item.title, "Test Movie")

    def test_add_or_update_missing_required_field(self):
        """Fehlende required fields werfen ValueError"""
        data = {
            "title": "Incomplete Data",
            "type": "movie"
            # source und provider_id fehlen!
        }
        with self.assertRaises(ValueError) as context:
            self.manager.add_or_update(data)
        self.assertIn("Required field missing", str(context.exception))

    def test_add_or_update_invalid_type(self):
        """Invalider Typ wirft ValueError"""
        data = {
            "title": "Invalid Type",
            "type": "invalid_type",  # Nicht in allowed_types
            "source": "netflix",
            "provider_id": "99999"
        }
        with self.assertRaises(ValueError) as context:
            self.manager.add_or_update(data)
        self.assertIn("Invalid type", str(context.exception))

    def test_add_or_update_negative_length(self):
        """Negative length_seconds wirft ValueError"""
        data = {
            "title": "Negative Length",
            "type": "movie",
            "source": "netflix",
            "provider_id": "88888",
            "length_seconds": -100  # Negativ!
        }
        with self.assertRaises(ValueError) as context:
            self.manager.add_or_update(data)
        self.assertIn("cannot be negative", str(context.exception))

    def test_add_or_update_duplicate_updates_timestamp(self):
        """Duplicate Einträge aktualisieren last_opened_at"""
        data = {
            "title": "Duplicate Test",
            "type": "movie",
            "source": "netflix",
            "provider_id": "77777",
            "has_real_id": True
        }

        # Erstes Insert
        self.manager.add_or_update(data)
        item1 = self.manager.get_by_provider("77777", "netflix")
        timestamp1 = item1.last_opened_at

        # Warte kurz, dann zweites Insert
        import time
        time.sleep(0.01)
        self.manager.add_or_update(data)

        item2 = self.manager.get_by_provider("77777", "netflix")
        timestamp2 = item2.last_opened_at

        # Timestamp sollte aktualisiert sein
        self.assertNotEqual(timestamp1, timestamp2)

    def test_list_by_type_filters_correctly(self):
        """list_by_type filtert nach Typ"""
        # Verschiedene Typen einfügen
        self.manager.add_or_update({
            "title": "Movie 1", "type": "movie", "source": "netflix", "provider_id": "m1"
        })
        self.manager.add_or_update({
            "title": "Movie 2", "type": "movie", "source": "netflix", "provider_id": "m2"
        })
        self.manager.add_or_update({
            "title": "Song 1", "type": "music", "source": "spotify", "provider_id": "s1"
        })

        movies = self.manager.list_by_type("movie")
        music = self.manager.list_by_type("music")

        self.assertEqual(len(movies), 2)
        self.assertEqual(len(music), 1)
        self.assertTrue(all(item.type == "movie" for item in movies))
        self.assertTrue(all(item.type == "music" for item in music))

    def test_list_by_type_excludes_blacklisted(self):
        """list_by_type filtert geblacklistete Items aus"""
        # Normal und blacklisted Items einfügen
        self.manager.add_or_update({
            "title": "Normal Movie", "type": "movie", "source": "netflix", "provider_id": "n1"
        })
        self.manager.add_or_update({
            "title": "Blacklisted Movie", "type": "movie", "source": "netflix", "provider_id": "b1"
        })

        # Zweites Item blacklisten
        self.db.execute(
            "UPDATE media_items SET blacklist_flag = 1 WHERE provider_id = ?",
            ("b1",)
        )

        movies = self.manager.list_by_type("movie")
        self.assertEqual(len(movies), 1)
        self.assertEqual(movies[0].title, "Normal Movie")


class TestBlacklistManager(unittest.TestCase):
    """Integration Tests für BlacklistManager"""

    def setUp(self):
        """Erstellt temporäre Test-Datenbank für jeden Test"""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        self.db = Database(self.db_path)
        self.media_manager = MediaManager(self.db)
        self.blacklist_manager = BlacklistManager(self.db)

    def tearDown(self):
        """Räumt temporäre Datenbank auf"""
        self.db.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_set_blacklist_enables(self):
        """set_blacklist aktiviert Blacklist"""
        # Item einfügen
        self.media_manager.add_or_update({
            "title": "Test Item", "type": "movie", "source": "netflix", "provider_id": "test1"
        })
        item = self.media_manager.get_by_provider("test1", "netflix")

        # Blacklist setzen
        self.blacklist_manager.set_blacklist(item.id, True, procedure_code=1)

        # Prüfen
        updated_item = self.media_manager.get_by_provider("test1", "netflix")
        self.assertEqual(updated_item.blacklist_flag, 1)
        self.assertEqual(updated_item.procedure_code, 1)
        self.assertIsNotNone(updated_item.blacklisted_at)

    def test_set_blacklist_disables(self):
        """set_blacklist deaktiviert Blacklist"""
        # Item mit Blacklist einfügen
        self.media_manager.add_or_update({
            "title": "Blacklisted Item", "type": "movie", "source": "netflix", "provider_id": "test2"
        })
        item = self.media_manager.get_by_provider("test2", "netflix")

        # Aktivieren und dann deaktivieren
        self.blacklist_manager.set_blacklist(item.id, True, procedure_code=2)
        self.blacklist_manager.set_blacklist(item.id, False)

        # Prüfen
        updated_item = self.media_manager.get_by_provider("test2", "netflix")
        self.assertEqual(updated_item.blacklist_flag, 0)
        self.assertEqual(updated_item.procedure_code, 0)
        self.assertIsNone(updated_item.blacklisted_at)


if __name__ == "__main__":
    unittest.main()
