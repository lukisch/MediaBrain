#!/usr/bin/env python3
"""
Patch: Erweitert MediaDetailView um Online-Metadaten-Anzeige.
Aufgabe: GUI - Metadaten im Detail-Panel anzeigen
"""
import re
from pathlib import Path

GUI_FILE = Path(__file__).parent / "gui.py"

def patch():
    # Backup erstellen
    content = GUI_FILE.read_text(encoding="utf-8")
    backup = GUI_FILE.with_suffix(".py.bak")
    backup.write_text(content, encoding="utf-8")
    print(f"Backup erstellt: {backup}")

    # 1. NEUE IMPORTS: Am Anfang nach "from pathlib import Path" einfuegen
    old_import = "from pathlib import Path"
    new_import = """from pathlib import Path
from threading import Thread"""
    
    if "from threading import Thread" not in content:
        content = content.replace(old_import, new_import)
        print("[OK] Thread-Import hinzugefuegt")
    
    # 2. MediaDetailView komplett ersetzen
    # Original MediaDetailView finden und ersetzen
    
    old_class = '''class MediaDetailView(QWidget):
    def __init__(self, item: MediaItem, media_manager: MediaManager, blacklist_manager: BlacklistManager, back_callback):
        super().__init__()

        self.item = item
        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager
        self.back_callback = back_callback

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Titel
        title = QLabel(item.title)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Thumbnail
        if item.thumbnail_url:
            thumb = QLabel(f"[Thumbnail: {item.thumbnail_url}]")
            layout.addWidget(thumb)

        # Beschreibung
        desc = QLabel(item.description or "Keine Beschreibung verfuegbar.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Metadaten
        meta = QLabel(
            f"Typ: {item.type}\\n"
            f"Provider: {item.source}\\n"
            f"Provider-ID: {item.provider_id}\\n"
            f"Erstellt am: {item.created_at}\\n"
            f"Zuletzt geoeffnet: {item.last_opened_at}\\n"
            f"Oeffnungsmethode: {item.open_method or '-'}"
        )
        layout.addWidget(meta)

        # Buttons
        btn_row = QHBoxLayout()

        open_btn = QPushButton("Oeffnen")
        open_btn.clicked.connect(self.open_item)
        btn_row.addWidget(open_btn)

        fav_btn = QPushButton("Favorit" if not item.is_favorite else "Favorit entfernen")
        fav_btn.clicked.connect(self.toggle_favorite)
        btn_row.addWidget(fav_btn)

        back_btn = QPushButton("Zurueck")
        back_btn.clicked.connect(self.back_callback)
        btn_row.addWidget(back_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def open_item(self):
        from core import OpenHandler
        handler = OpenHandler(self.media_manager)
        handler.open_item(self.item)

    def toggle_favorite(self):
        new_value = 0 if self.item.is_favorite else 1
        self.media_manager.db.execute(
            "UPDATE media_items SET is_favorite = ? WHERE id = ?",
            (new_value, self.item.id)
        )
        from MediaBrain import controller
        controller.notify_data_changed()'''
    
    new_class = '''class MediaDetailView(QWidget):
    """Detailansicht fuer ein Medium - zeigt alle verfuegbaren Metadaten."""
    
    def __init__(self, item: MediaItem, media_manager: MediaManager, blacklist_manager: BlacklistManager, back_callback):
        super().__init__()

        self.item = item
        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager
        self.back_callback = back_callback

        layout = QVBoxLayout()
        self.setLayout(layout)

        # === HEADER: Titel + Typ-Icon ===
        header_row = QHBoxLayout()
        icon = QLabel("🎬" if item.type == "movie" else "🎵" if item.type == "music" else "📺")
        icon.setStyleSheet("font-size: 24px;")
        header_row.addWidget(icon)
        
        title = QLabel(item.title)
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_row.addWidget(title)
        header_row.addStretch()
        layout.addLayout(header_row)

        # === THUMBNAIL ===
        if item.thumbnail_url:
            thumb = QLabel(f"[Thumbnail: {item.thumbnail_url}]")
            thumb.setStyleSheet("color: #888; font-style: italic;")
            layout.addWidget(thumb)

        # === BESCHREIBUNG ===
        desc_label = QLabel("Beschreibung:")
        desc_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(desc_label)
        
        desc = QLabel(item.description or "Keine Beschreibung verfuegbar.")
        desc.setWordWrap(True)
        desc.setStyleSheet("padding-left: 10px;")
        layout.addWidget(desc)

        # === LOKALE METADATEN ===
        local_label = QLabel("Lokale Daten:")
        local_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(local_label)
        
        meta = QLabel(
            f"  Typ: {item.type}\\n"
            f"  Provider: {item.source}\\n"
            f"  Provider-ID: {item.provider_id or '-'}\\n"
            f"  Erstellt am: {item.created_at or '-'}\\n"
            f"  Zuletzt geoeffnet: {item.last_opened_at or '-'}\\n"
            f"  Oeffnungsmethode: {item.open_method or 'auto'}"
        )
        meta.setStyleSheet("padding-left: 10px; font-family: monospace;")
        layout.addWidget(meta)

        # === ONLINE METADATEN (dynamisch) ===
        online_label = QLabel("Online Metadaten:")
        online_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(online_label)
        
        self.online_meta_container = QVBoxLayout()
        self.online_meta_label = QLabel("Lade Online-Metadaten...")
        self.online_meta_label.setStyleSheet("padding-left: 10px; color: #888;")
        self.online_meta_container.addWidget(self.online_meta_label)
        layout.addLayout(self.online_meta_container)
        
        # Online-Metadaten im Hintergrund laden
        self._load_online_metadata()

        # === BUTTONS ===
        btn_row = QHBoxLayout()

        open_btn = QPushButton("Oeffnen")
        open_btn.clicked.connect(self.open_item)
        btn_row.addWidget(open_btn)

        fav_btn = QPushButton("Favorit" if not item.is_favorite else "Favorit entfernen")
        fav_btn.clicked.connect(self.toggle_favorite)
        btn_row.addWidget(fav_btn)
        
        fetch_btn = QPushButton("🌐 Metadaten aktualisieren")
        fetch_btn.clicked.connect(self._fetch_and_save_metadata)
        btn_row.addWidget(fetch_btn)

        back_btn = QPushButton("Zurueck")
        back_btn.clicked.connect(self.back_callback)
        btn_row.addWidget(back_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        
        layout.addStretch()

    def _load_online_metadata(self):
        """Laedt Online-Metadaten asynchron."""
        def fetch():
            try:
                from metadata_v2 import MetadataFetcher
                fetcher = MetadataFetcher()
                result = fetcher.auto_fetch(
                    title=self.item.title,
                    media_type=self.item.type,
                    year=getattr(self.item, 'year', None),
                    artist=getattr(self.item, 'artist', None)
                )
                # UI im Main-Thread aktualisieren
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_update_online_metadata",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(object, result)
                )
            except Exception as e:
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_update_online_metadata",
                    Qt.ConnectionType.QueuedConnection,
                    Q_ARG(object, {"error": str(e)})
                )
        
        Thread(target=fetch, daemon=True).start()
    
    def _update_online_metadata(self, result):
        """Aktualisiert die Online-Metadaten-Anzeige."""
        self.online_meta_label.deleteLater()
        
        if not result:
            label = QLabel("  Keine Online-Metadaten gefunden.")
            label.setStyleSheet("padding-left: 10px; color: #888;")
            self.online_meta_container.addWidget(label)
            return
        
        if "error" in result:
            label = QLabel(f"  Fehler: {result['error']}")
            label.setStyleSheet("padding-left: 10px; color: red;")
            self.online_meta_container.addWidget(label)
            return
        
        # Metadaten formatiert anzeigen
        lines = []
        if result.get("title"):
            lines.append(f"  Titel: {result['title']}")
        if result.get("year"):
            lines.append(f"  Jahr: {result['year']}")
        if result.get("rating"):
            lines.append(f"  Bewertung: {result['rating']}/10")
        if result.get("genres"):
            lines.append(f"  Genres: {', '.join(result['genres']) if isinstance(result['genres'], list) else result['genres']}")
        if result.get("runtime"):
            lines.append(f"  Laufzeit: {result['runtime']} Min")
        if result.get("director"):
            lines.append(f"  Regie: {result['director']}")
        if result.get("source"):
            lines.append(f"  Quelle: {result['source']}")
        
        if lines:
            meta_text = "\\n".join(lines)
            label = QLabel(meta_text)
            label.setStyleSheet("padding-left: 10px; font-family: monospace;")
            self.online_meta_container.addWidget(label)
        
        # Beschreibung separat (falls laenger)
        if result.get("description") and result["description"] != self.item.description:
            desc_label = QLabel("Online-Beschreibung:")
            desc_label.setStyleSheet("font-weight: bold; margin-top: 10px; padding-left: 10px;")
            self.online_meta_container.addWidget(desc_label)
            
            desc = QLabel(result["description"][:500] + "..." if len(result.get("description", "")) > 500 else result.get("description", ""))
            desc.setWordWrap(True)
            desc.setStyleSheet("padding-left: 20px; color: #555;")
            self.online_meta_container.addWidget(desc)

    def _fetch_and_save_metadata(self):
        """Holt Metadaten und speichert sie in der Datenbank."""
        from PyQt6.QtWidgets import QMessageBox
        try:
            from metadata_v2 import MetadataFetcher
            fetcher = MetadataFetcher()
            result = fetcher.auto_fetch(
                title=self.item.title,
                media_type=self.item.type
            )
            
            if not result:
                QMessageBox.information(self, "Keine Daten", "Keine Online-Metadaten gefunden.")
                return
            
            # DB Update
            updates = []
            params = []
            
            if result.get("description"):
                updates.append("description = ?")
                params.append(result["description"])
            if result.get("thumbnail_url"):
                updates.append("thumbnail_url = ?")
                params.append(result["thumbnail_url"])
            if result.get("rating"):
                updates.append("rating = ?")
                params.append(result["rating"])
            
            if updates:
                params.append(self.item.id)
                query = f"UPDATE media_items SET {', '.join(updates)} WHERE id = ?"
                self.media_manager.db.execute(query, tuple(params))
                
                QMessageBox.information(self, "Gespeichert", 
                    f"Metadaten aktualisiert. Quelle: {result.get('source', 'unbekannt')}")
                
                from MediaBrain import controller
                controller.notify_data_changed()
            else:
                QMessageBox.information(self, "Keine Aenderungen", "Keine neuen Daten zum Speichern.")
                
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Fehler beim Abrufen: {e}")

    def open_item(self):
        from core import OpenHandler
        handler = OpenHandler(self.media_manager)
        handler.open_item(self.item)

    def toggle_favorite(self):
        new_value = 0 if self.item.is_favorite else 1
        self.media_manager.db.execute(
            "UPDATE media_items SET is_favorite = ? WHERE id = ?",
            (new_value, self.item.id)
        )
        from MediaBrain import controller
        controller.notify_data_changed()'''
    
    # Ersetzen (vorsichtig - exakter Match)
    if old_class in content:
        content = content.replace(old_class, new_class)
        print("[OK] MediaDetailView erweitert")
    else:
        # Fallback: Versuche mit Regex zu finden
        print("[WARN] Exakter Match fehlgeschlagen - manuelles Patching noetig")
        print("Bitte die Klasse MediaDetailView manuell durch den neuen Code ersetzen.")
        return False
    
    # Speichern
    GUI_FILE.write_text(content, encoding="utf-8")
    print(f"[OK] {GUI_FILE} aktualisiert")
    return True

if __name__ == "__main__":
    if patch():
        print("\n✅ Patch erfolgreich!")
        print("Die MediaDetailView zeigt jetzt Online-Metadaten an.")
    else:
        print("\n❌ Patch fehlgeschlagen - manuelles Eingreifen noetig")
