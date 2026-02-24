"""
gui.py – Erweiterte GUI für MediaBrain
- Sidebar Navigation
- Globale Suche
- Favoriten-Ansicht
- Einstellungen-Fenster
- Verbesserte MediaItemWidgets
"""

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton, QLineEdit,
    QStackedWidget, QMenu, QScrollArea, QFrame, QSplitter, QTabWidget,
    QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon

from core import MediaManager, MediaItem, BlacklistManager
import config
from pathlib import Path

# Erweiterte Suche
from search_advanced import AdvancedSearchBar, SearchEngine, SearchCriteria

def notify_gui_refresh():
    """Benachrichtigt die GUI über Änderungen, ohne MediaBrain.py zu importieren (verhindert Circular Import)."""
    mw = QApplication.activeWindow()
    # Falls das aktive Fenster nicht das MainWindow ist (z.B. ein Dialog),
    # suchen wir in allen Top-Level-Widgets
    if not mw or not hasattr(mw, "refresh_all_views"):
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, "refresh_all_views"):
                mw = widget
                break

    if mw and hasattr(mw, "refresh_all_views"):
        mw.refresh_all_views()


# ============================================================
# 1. Suchleiste
# ============================================================

class SearchBar(QWidget):
    def __init__(self, placeholder="Suchen...", on_search=None):
        super().__init__()
        self.on_search = on_search

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.input = QLineEdit()
        self.input.setPlaceholderText(placeholder)
        self.input.textChanged.connect(self._trigger_search)

        layout.addWidget(self.input)

    def _trigger_search(self):
        if self.on_search:
            self.on_search(self.input.text())


# ============================================================
# 2. Collapsible Panel
# ============================================================

class CollapsiblePanel(QWidget):
    def __init__(self, title="Details", content_widget=None):
        super().__init__()

        self.is_open = False

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.header = QPushButton(title)
        self.header.setCheckable(True)
        self.header.clicked.connect(self.toggle)
        self.main_layout.addWidget(self.header)

        self.content = content_widget or QLabel("Keine Details verfügbar")
        self.content.setVisible(False)
        self.main_layout.addWidget(self.content)

    def toggle(self):
        self.is_open = not self.is_open
        self.content.setVisible(self.is_open)


# ============================================================
# 3. MediaItemWidget (verbessert)
# ============================================================

class MediaItemWidget(QFrame):
    def __init__(self, item: MediaItem, media_manager: MediaManager, blacklist_manager: BlacklistManager):
        super().__init__()
        self.item = item
        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager

        self.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
        self.setStyleSheet("padding: 8px;")

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Titel + Icon
        title_row = QHBoxLayout()
        icon = QLabel("🎬" if item.type == "movie" else "🎵" if item.type == "music" else "📺")
        icon.setFixedWidth(30)
        title_row.addWidget(icon)

        title_label = QLabel(f"{item.title} ({item.source})")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Buttons
        btn_row = QHBoxLayout()
        open_btn = QPushButton("Öffnen")
        open_btn.clicked.connect(self.open_item)
        btn_row.addWidget(open_btn)

        fav_btn = QPushButton("★" if item.is_favorite else "☆")
        fav_btn.clicked.connect(self.toggle_favorite)
        btn_row.addWidget(fav_btn)

        details_btn = QPushButton("Details")
        details_btn.clicked.connect(self.open_detail_page)
        btn_row.addWidget(details_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Details Panel
        details = QLabel(
            f"Beschreibung: {item.description or '-'}\n"
            f"Staffel: {item.season or '-'} | Episode: {item.episode or '-'}\n"
            f"Künstler: {item.artist or '-'} | Album: {item.album or '-'}"
        )
        self.details_panel = CollapsiblePanel("Details anzeigen", details)
        layout.addWidget(self.details_panel)

        # Kontextmenü
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.open_context_menu)

    def open_item(self):
        try:
            from core import OpenHandler
            handler = OpenHandler(self.media_manager)
            handler.open_item(self.item)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Konnte Medium nicht oeffnen: {e}")

    def open_detail_page(self):
        try:
            from gui import MainWindow
            mw = QApplication.activeWindow()
            if hasattr(mw, "open_detail"):
                mw.open_detail(self.item)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Detailseite konnte nicht geoeffnet werden: {e}")

    def toggle_favorite(self):
        try:
            new_value = 0 if self.item.is_favorite else 1
            self.media_manager.db.execute(
                "UPDATE media_items SET is_favorite = ? WHERE id = ?",
                (new_value, self.item.id)
            )
            notify_gui_refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Favorit konnte nicht geaendert werden: {e}")


    def toggle_details(self):
        self.details_panel.toggle()
    def show_in_explorer(self):
        try:
            import subprocess, platform, os
            path = self.item.local_path

            system = platform.system()
            if system == "Windows":
                subprocess.Popen(["explorer", "/select,", path])
            elif system == "Darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                folder = os.path.dirname(path)
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Konnte Datei nicht im Explorer anzeigen: {e}")

    def delete_file(self):
        try:
            import os
            if os.path.exists(self.item.local_path):
                os.remove(self.item.local_path)

            self.media_manager.db.execute(
                "DELETE FROM media_items WHERE id = ?",
                (self.item.id,)
            )
            notify_gui_refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Datei konnte nicht geloescht werden: {e}")

    def refresh_metadata(self):
        # Später: ID3/MP4 neu einlesen
        print("[Meta] Metadaten aktualisieren (noch nicht implementiert)")

    def open_context_menu(self, pos):
        menu = QMenu(self)

        fav_action = QAction("Favorit entfernen" if self.item.is_favorite else "Als Favorit markieren")
        fav_action.triggered.connect(self.toggle_favorite)
        menu.addAction(fav_action)

        temp_delete_action = QAction("Temporär ausblenden")
        temp_delete_action.triggered.connect(self.temp_delete)
        menu.addAction(temp_delete_action)

        blacklist_menu = menu.addMenu("Blacklist…")
        for code, label in [
            (1, "1 Tag"),
            (2, "1 Woche"),
            (3, "1 Monat"),
            (4, "3 Monate"),
            (5, "1 Jahr"),
            (6, "Für immer")
        ]:
            act = QAction(label)
            act.triggered.connect(lambda _, c=code: self.blacklist(c))
            blacklist_menu.addAction(act)

        if self.item.blacklist_flag == 1:
            unblack = QAction("Blacklist entfernen")
            unblack.triggered.connect(lambda: self.blacklist_manager.set_blacklist(self.item.id, False))
            menu.addAction(unblack)

        menu.addSeparator()

        # Datei-Aktionen (nur für lokale Dateien)
        if self.item.is_local_file:
            show_action = QAction("Im Explorer anzeigen")
            show_action.triggered.connect(self.show_in_explorer)
            menu.addAction(show_action)

            if config.config.get("allow_file_deletion"):
                delete_action = QAction("Datei löschen")
                delete_action.triggered.connect(self.delete_file)
                menu.addAction(delete_action)

            meta_action = QAction("Lokale Metadaten aktualisieren")
            meta_action.triggered.connect(self.refresh_metadata)
            menu.addAction(meta_action)

        # Online-Metadaten abrufen (NEU!)
        online_meta_action = QAction("🌐 Online-Metadaten abrufen")
        online_meta_action.triggered.connect(self.fetch_online_metadata)
        menu.addAction(online_meta_action)

        menu.exec(self.mapToGlobal(pos))

    def temp_delete(self):
        try:
            from datetime import datetime
            self.media_manager.db.execute(
                "UPDATE media_items SET blacklist_flag = 1, procedure_code = 1, blacklisted_at = ? WHERE id = ?",
                (datetime.now().isoformat(), self.item.id)
            )
            notify_gui_refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Temporaeres Ausblenden fehlgeschlagen: {e}")

    def blacklist(self, code):
        try:
            self.blacklist_manager.set_blacklist(self.item.id, True, code)
            notify_gui_refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Blacklist-Aktion fehlgeschlagen: {e}")

    def fetch_online_metadata(self):
        """Holt Online-Metadaten von TMDb/OMDb/MusicBrainz und aktualisiert den DB-Eintrag."""
        from metadata_v2 import MetadataFetcher
        from PyQt6.QtWidgets import QMessageBox

        try:
            fetcher = MetadataFetcher()

            # Status prüfen
            status = fetcher.get_status()
            if not any(status.values()):
                QMessageBox.warning(self, "API nicht verfügbar",
                    "Keine API-Keys konfiguriert. Bitte in settings.json eintragen.")
                return

            # Metadaten basierend auf Typ abrufen
            result = fetcher.auto_fetch(
                title=self.item.title,
                media_type=self.item.type,
                year=getattr(self.item, 'year', None),
                artist=getattr(self.item, 'artist', None)
            )

            if not result:
                QMessageBox.information(self, "Keine Ergebnisse",
                    f"Keine Online-Metadaten gefunden für '{self.item.title}'")
                return

            # Datenbank aktualisieren
            updates = []
            params = []

            if result.get("description") and result["description"] != self.item.description:
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

                QMessageBox.information(self, "Metadaten aktualisiert",
                    f"Metadaten für '{result.get('title', self.item.title)}' wurden aktualisiert.\n"
                    f"Quelle: {result.get('source', 'unbekannt')}")

                # GUI aktualisieren
                notify_gui_refresh()
            else:
                QMessageBox.information(self, "Keine neuen Daten",
                    "Die gefundenen Metadaten sind bereits identisch.")
        except Exception as e:
            QMessageBox.critical(self, "Fehler",
                f"Metadaten konnten nicht abgerufen werden: {e}")


# Duplikat blacklist() entfernt - existiert bereits in Zeile 285 mit Error-Handling


from PyQt6.QtCore import QAbstractListModel, Qt, QModelIndex
from PyQt6.QtWidgets import QListView, QMenu

# --- 1. Das Daten-Modell (Hält die Daten effizient im Speicher) ---
class MediaListModel(QAbstractListModel):
    def __init__(self, media_items=None):
        super().__init__()
        self.media_items = media_items or []

    def data(self, index, role):
        if not index.isValid() or index.row() >= len(self.media_items):
            return None
        
        item = self.media_items[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            # Was im Listen-Eintrag als Text steht
            fav_mark = "★ " if item.is_favorite else ""
            return f"{fav_mark}{item.title} ({item.source})"
        
        if role == Qt.ItemDataRole.ToolTipRole:
            # Mouseover Info
            return f"{item.description}\nQuelle: {item.source}"

        if role == Qt.ItemDataRole.UserRole:
            # Gibt das ganze Objekt zurück für Zugriff in der View
            return item
            
        return None

    def rowCount(self, index):
        return len(self.media_items)

    def update_data(self, new_items):
        """Aktualisiert die Liste komplett neu"""
        self.beginResetModel()
        self.media_items = new_items
        self.endResetModel()


# --- 2. Die optimierte View (Zeigt die Liste an) ---
class LibraryView(QWidget):
    def __init__(self, media_type, media_manager: MediaManager, blacklist_manager: BlacklistManager):
        super().__init__()
        self.media_type = media_type
        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager
        
        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Suche (Erweitert)
        self.search_bar = AdvancedSearchBar()
        self.search_bar.search_triggered.connect(self.apply_search)
        layout.addWidget(self.search_bar)

        # Die leistungsfähige Liste (Ersetzt ScrollArea)
        self.list_view = QListView()
        self.model = MediaListModel()
        self.list_view.setModel(self.model)
        self.list_view.setAlternatingRowColors(True)
        
        # Interaktionen
        self.list_view.doubleClicked.connect(self.open_item_by_click)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.open_context_menu)

        layout.addWidget(self.list_view)
        
        # Initial laden
        self.refresh()

    def refresh(self):
        # Daten holen
        items = self.media_manager.list_by_type(self.media_type)
        # Hier könnte man noch sortieren (analog zu vorher)
        self.model.update_data(items)

    def apply_search(self, criteria: SearchCriteria):
        # Suche ausführen via SearchEngine (erweitert)
        engine = SearchEngine(self.media_manager.db)
        # Typ erzwingen (da wir in einer Library-View sind)
        criteria.media_type = self.media_type
        results = engine.search(criteria)
        self.model.update_data(results)

    def open_item_by_click(self, index):
        item = self.model.data(index, Qt.ItemDataRole.UserRole)
        if item:
            from core import OpenHandler
            handler = OpenHandler(self.media_manager)
            handler.open_item(item)

    def open_context_menu(self, pos):
        index = self.list_view.indexAt(pos)
        if not index.isValid():
            return
            
        item = self.model.data(index, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        # Aktionen
        act_open = QAction("Öffnen", self)
        act_open.triggered.connect(lambda: self.open_item_by_click(index))
        menu.addAction(act_open)

        act_fav = QAction("Favorit entfernen" if item.is_favorite else "Zu Favoriten", self)
        act_fav.triggered.connect(lambda: self.toggle_favorite(item))
        menu.addAction(act_fav)
        
        menu.addSeparator()
        
        act_details = QAction("Details anzeigen", self)
        act_details.triggered.connect(lambda: self.show_details(item))
        menu.addAction(act_details)
        
        # Blacklist Submenü
        bl_menu = menu.addMenu("Auf Blacklist setzen")
        # (Hier Codes wie in deinem alten Code einfügen)
        act_forever = QAction("Für immer blockieren", self)
        act_forever.triggered.connect(lambda: self.blacklist_manager.set_blacklist(item.id, True, 6))
        bl_menu.addAction(act_forever)

        menu.exec(self.list_view.mapToGlobal(pos))

    def toggle_favorite(self, item):
        new_val = 0 if item.is_favorite else 1
        self.media_manager.db.execute("UPDATE media_items SET is_favorite=? WHERE id=?", (new_val, item.id))
        self.refresh() # Liste neu laden
        
    def show_details(self, item):
        # Zugriff auf MainWindow um Detailseite zu öffnen
        mw = QApplication.activeWindow()
        if hasattr(mw, "open_detail"):
            mw.open_detail(item)
# ============================================================
# 5. FavoritenView
# ============================================================

class FavoritesView(QWidget):
    def __init__(self, media_manager: MediaManager, blacklist_manager: BlacklistManager):
        super().__init__()
        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager

        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel("Favoriten"))

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)
        self.scroll.setWidget(self.container)

        self.refresh()

    def refresh(self):
        try:
            for i in reversed(range(self.container_layout.count())):
                widget = self.container_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            rows = self.media_manager.db.fetchall("""
                SELECT * FROM media_items
                WHERE is_favorite = 1 AND blacklist_flag = 0
                ORDER BY last_opened_at DESC
            """)

            for row in rows:
                item = MediaItem(row)
                widget = MediaItemWidget(item, self.media_manager, self.blacklist_manager)
                self.container_layout.addWidget(widget)

            self.container_layout.addStretch()
        except Exception as e:
            self.container_layout.addWidget(QLabel(f"Fehler beim Laden der Favoriten: {e}"))


# ============================================================
# 6. Globale Suche
# ============================================================

class GlobalSearchView(QWidget):
    def __init__(self, media_manager: MediaManager, blacklist_manager: BlacklistManager):
        super().__init__()
        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.search_bar = AdvancedSearchBar()
        self.search_bar.search_triggered.connect(self.apply_search)
        layout.addWidget(self.search_bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)
        self.scroll.setWidget(self.container)

    def apply_search(self, criteria: SearchCriteria):
        try:
            for i in reversed(range(self.container_layout.count())):
                widget = self.container_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()

            if not criteria.text.strip() and not criteria.provider and not criteria.media_type:
                return

            engine = SearchEngine(self.media_manager.db)
            results = engine.search(criteria)

            for item in results:
                widget = MediaItemWidget(item, self.media_manager, self.blacklist_manager)
                self.container_layout.addWidget(widget)

            self.container_layout.addStretch()
        except Exception as e:
            self.container_layout.addWidget(QLabel(f"Suchfehler: {e}"))


# ============================================================
# 7. Einstellungen-Fenster
# ============================================================

class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Einstellungen")
        self.resize(600, 400)

        layout = QVBoxLayout()
        self.setLayout(layout)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Allgemein
        general = QWidget()
        g_layout = QVBoxLayout()
        general.setLayout(g_layout)

        theme_label = QLabel("Theme:")
        theme_select = QComboBox()
        theme_select.addItems(["light", "dark"])
        theme_select.setCurrentText(config.config.get("ui.theme"))
        def on_theme_change(value):
            config.config.set("ui.theme", value)
            # Dynamisch anwenden
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, "apply_theme"):
                    widget.apply_theme()
        theme_select.currentTextChanged.connect(on_theme_change)

        g_layout.addWidget(theme_label)
        g_layout.addWidget(theme_select)
        g_layout.addStretch()

        tabs.addTab(general, "Allgemein")

        # Provider
        provider = QWidget()
        p_layout = QVBoxLayout()
        provider.setLayout(p_layout)

        for name in config.config.get("providers").keys():
            label = QLabel(f"{name} Öffnen mit:")
            combo = QComboBox()
            combo.addItems(["browser", "app", "local", "auto"])
            combo.setCurrentText(config.config.get(f"providers.{name}.preferred_open_method"))
            combo.currentTextChanged.connect(
                lambda v, n=name: config.config.set(f"providers.{n}.preferred_open_method", v)
            )
            p_layout.addWidget(label)
            p_layout.addWidget(combo)

        p_layout.addStretch()
        tabs.addTab(provider, "Provider")

        # Sicherheit
        security = QWidget()
        s_layout = QVBoxLayout()
        security.setLayout(s_layout)

        delete_checkbox = QCheckBox("Löschen lokaler Dateien erlauben")
        delete_checkbox.setChecked(config.config.get("allow_file_deletion"))
        delete_checkbox.stateChanged.connect(
            lambda v: config.config.set("allow_file_deletion", bool(v))
        )

        s_layout.addWidget(delete_checkbox)
        s_layout.addStretch()

        tabs.addTab(security, "Sicherheit")



# ============================================================
# DashboardView – zentrale Startseite
# ============================================================

# In gui.py

class DashboardView(QWidget):
    def __init__(self, media_manager: MediaManager, blacklist_manager: BlacklistManager, open_settings_callback=None, open_blacklist_callback=None):
        super().__init__()

        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager
        
        # SearchEngine für erweiterte Suche
        self.search_engine = SearchEngine(self.media_manager.db)
        
        # Callbacks speichern
        self.open_settings_callback = open_settings_callback
        self.open_blacklist_callback = open_blacklist_callback

        layout = QVBoxLayout()
        self.setLayout(layout)

        # 1. Erweiterte Suche (ersetzt alte SearchBar)
        self.search_bar = AdvancedSearchBar()
        self.search_bar.search_triggered.connect(self.apply_search)
        layout.addWidget(self.search_bar)

        # 2. Quick Actions (Statisch - wird nicht neu geladen -> KEIN FLACKERN MEHR)
        actions_layout = QHBoxLayout()
        
        btn_scan = QPushButton("Bibliothek scannen")
        # btn_scan.clicked.connect(...) # Später Funktion einbauen
        actions_layout.addWidget(btn_scan)

        btn_settings = QPushButton("Einstellungen")
        if self.open_settings_callback:
            btn_settings.clicked.connect(self.open_settings_callback)
        actions_layout.addWidget(btn_settings)

        btn_bl = QPushButton("Blacklist anzeigen")
        if self.open_blacklist_callback:
            btn_bl.clicked.connect(self.open_blacklist_callback)
        actions_layout.addWidget(btn_bl)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # 3. Scrollbereich für dynamischen Inhalt
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        # Rahmen entfernen für saubereren Look
        self.scroll.setFrameShape(QFrame.Shape.NoFrame) 
        layout.addWidget(self.scroll)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)
        self.scroll.setWidget(self.container)

        self.refresh()

    def refresh(self):
        try:
            while self.container_layout.count():
                item = self.container_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

            # --- A. Favoriten ---
            fav_label = QLabel("Favoriten")
            fav_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
            self.container_layout.addWidget(fav_label)

            fav_rows = self.media_manager.db.fetchall("""
                SELECT * FROM media_items
                WHERE is_favorite = 1 AND blacklist_flag = 0
                ORDER BY last_opened_at DESC
                LIMIT 5
            """)

            if fav_rows:
                for row in fav_rows:
                    item = MediaItem(row)
                    widget = MediaItemWidget(item, self.media_manager, self.blacklist_manager)
                    self.container_layout.addWidget(widget)
            else:
                self.container_layout.addWidget(QLabel("Keine Favoriten markiert."))

            # --- B. Zuletzt geöffnet ---
            recent_label = QLabel("Zuletzt geoeffnet")
            recent_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 20px;")
            self.container_layout.addWidget(recent_label)

            recent_rows = self.media_manager.db.fetchall("""
                SELECT * FROM media_items
                WHERE blacklist_flag = 0
                ORDER BY last_opened_at DESC
                LIMIT 10
            """)

            if recent_rows:
                for row in recent_rows:
                    item = MediaItem(row)
                    widget = MediaItemWidget(item, self.media_manager, self.blacklist_manager)
                    self.container_layout.addWidget(widget)
            else:
                self.container_layout.addWidget(QLabel("Noch keine Aktivitaeten."))

            self.container_layout.addStretch()
        except Exception as e:
            self.container_layout.addWidget(QLabel(f"Fehler beim Laden des Dashboards: {e}"))

    def apply_search(self, criteria: SearchCriteria):
        """Führt erweiterte Suche basierend auf SearchCriteria aus."""
        # Container leeren
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        # Prüfe ob Filter aktiv sind
        has_filters = (
            criteria.text.strip() or 
            criteria.media_type or 
            criteria.provider or 
            criteria.favorites_only or 
            criteria.time_filter_days or
            criteria.tags
        )
        
        if not has_filters:
            self.refresh()
            return

        # Suchinfo anzeigen
        filter_parts = []
        if criteria.text:
            filter_parts.append(f'"{criteria.text}"')
        if criteria.media_type:
            filter_parts.append(f"Typ: {criteria.media_type}")
        if criteria.provider:
            filter_parts.append(f"Provider: {criteria.provider}")
        if criteria.favorites_only:
            filter_parts.append("⭐ Favoriten")
        if criteria.time_filter_days:
            filter_parts.append(f"Letzte {criteria.time_filter_days} Tage")
            
        search_info = " | ".join(filter_parts) if filter_parts else "Alle"
        search_label = QLabel(f"🔍 Suche: {search_info}")
        search_label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 5px 0;")
        self.container_layout.addWidget(search_label)

        # Suche ausführen via SearchEngine
        results = self.search_engine.search(criteria)
        
        if results:
            count_label = QLabel(f"{len(results)} Ergebnisse gefunden")
            count_label.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 10px;")
            self.container_layout.addWidget(count_label)
            
            for media_item in results:
                widget = MediaItemWidget(media_item, self.media_manager, self.blacklist_manager)
                self.container_layout.addWidget(widget)
        else:
            no_results = QLabel("Keine Treffer gefunden.")
            no_results.setStyleSheet("color: gray; padding: 20px;")
            self.container_layout.addWidget(no_results)
            
        self.container_layout.addStretch()
# ============================================================
# BlacklistView – vollständige Verwaltung
# ============================================================

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QHBoxLayout,
    QPushButton, QComboBox, QFrame
)
from PyQt6.QtCore import Qt

class BlacklistView(QWidget):
    def __init__(self, media_manager: MediaManager, blacklist_manager: BlacklistManager):
        super().__init__()

        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager

        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Blacklist-Verwaltung")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # -------------------------------------------------------
        # Filterleiste
        # -------------------------------------------------------
        filter_row = QHBoxLayout()

        self.provider_filter = QComboBox()
        self.provider_filter.addItem("Alle Provider")
        for p in ["netflix", "youtube", "spotify", "local"]:
            self.provider_filter.addItem(p)
        self.provider_filter.currentTextChanged.connect(self.refresh)
        filter_row.addWidget(self.provider_filter)

        self.duration_filter = QComboBox()
        self.duration_filter.addItem("Alle Dauern")
        self.duration_filter.addItems([
            "1 Tag", "1 Woche", "1 Monat", "3 Monate", "1 Jahr", "Für immer"
        ])
        self.duration_filter.currentTextChanged.connect(self.refresh)
        filter_row.addWidget(self.duration_filter)

        self.expiry_filter = QComboBox()
        self.expiry_filter.addItem("Alle")
        self.expiry_filter.addItem("Nur abgelaufen")
        self.expiry_filter.addItem("Nur aktiv")
        self.expiry_filter.currentTextChanged.connect(self.refresh)
        filter_row.addWidget(self.expiry_filter)

        layout.addLayout(filter_row)

        # -------------------------------------------------------
        # Buttons
        # -------------------------------------------------------
        btn_row = QHBoxLayout()

        btn_clear_expired = QPushButton("Abgelaufene entfernen")
        btn_clear_expired.clicked.connect(self._remove_expired)
        btn_row.addWidget(btn_clear_expired)

        btn_clear_all = QPushButton("Alle entfernen")
        btn_clear_all.clicked.connect(self._remove_all)
        btn_row.addWidget(btn_clear_all)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # -------------------------------------------------------
        # Scrollbereich
        # -------------------------------------------------------
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)

        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)
        self.scroll.setWidget(self.container)

        self.refresh()

    # -----------------------------------------------------------
    # Ablaufdatum berechnen
    # -----------------------------------------------------------
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
            return None
        return None

    # -----------------------------------------------------------
    # Blacklist-Ansicht aktualisieren
    # -----------------------------------------------------------
    def refresh(self):
        # Container leeren
        for i in reversed(range(self.container_layout.count())):
            widget = self.container_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Daten laden
        rows = self.media_manager.db.fetchall("""
            SELECT *
            FROM media_items
            WHERE blacklist_flag = 1
            ORDER BY blacklisted_at DESC
        """)

        # Filter anwenden
        provider_filter = self.provider_filter.currentText()
        duration_filter = self.duration_filter.currentText()
        expiry_filter = self.expiry_filter.currentText()

        for row in rows:
            item = MediaItem(row)

            # Provider-Filter
            if provider_filter != "Alle Provider" and item.source != provider_filter:
                continue

            # Dauer-Filter
            if duration_filter != "Alle Dauern":
                code_map = {
                    "1 Tag": 1,
                    "1 Woche": 2,
                    "1 Monat": 3,
                    "3 Monate": 4,
                    "1 Jahr": 5,
                    "Für immer": 6
                }
                if item.procedure_code != code_map[duration_filter]:
                    continue

            # Ablauf-Filter
            if item.blacklisted_at:
                start = datetime.fromisoformat(item.blacklisted_at)
                expiry = self._expiry_date(start, item.procedure_code)
                expired = expiry and datetime.now() > expiry
            else:
                expired = False

            if expiry_filter == "Nur abgelaufen" and not expired:
                continue
            if expiry_filter == "Nur aktiv" and expired:
                continue

            # Widget erzeugen
            widget = self._create_blacklist_widget(item, expired, expiry)
            self.container_layout.addWidget(widget)

        self.container_layout.addStretch()

    # -----------------------------------------------------------
    # Einzelnes Blacklist-Widget
    # -----------------------------------------------------------
    def _create_blacklist_widget(self, item: MediaItem, expired: bool, expiry):
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Raised)
        frame.setStyleSheet("padding: 8px;")
        layout = QVBoxLayout()
        frame.setLayout(layout)

        title = QLabel(f"{item.title} ({item.source})")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        layout.addWidget(QLabel(f"Sperrcode: {item.procedure_code}"))
        layout.addWidget(QLabel(f"Seit: {item.blacklisted_at}"))

        if expiry:
            layout.addWidget(QLabel(f"Ablaufdatum: {expiry}"))
        else:
            layout.addWidget(QLabel("Ablaufdatum: Nie"))

        if expired:
            expired_label = QLabel("Status: Abgelaufen")
            expired_label.setStyleSheet("color: red; font-weight: bold;")
            layout.addWidget(expired_label)
        else:
            layout.addWidget(QLabel("Status: Aktiv"))

        # Buttons
        btn_row = QHBoxLayout()

        btn_remove = QPushButton("Entfernen")
        btn_remove.clicked.connect(lambda: self._remove_single(item.id))
        btn_row.addWidget(btn_remove)

        btn_change = QPushButton("Dauer ändern")
        btn_change.clicked.connect(lambda: self._change_duration(item.id))
        btn_row.addWidget(btn_change)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        return frame

    # -----------------------------------------------------------
    # Aktionen
    # -----------------------------------------------------------
    def _remove_single(self, item_id):
        try:
            self.blacklist_manager.set_blacklist(item_id, False)
            self.refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Blacklist-Eintrag konnte nicht entfernt werden: {e}")

    def _change_duration(self, item_id):
        try:
            self.blacklist_manager.set_blacklist(item_id, True, 2)
            self.refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Dauer konnte nicht geaendert werden: {e}")

    def _remove_expired(self):
        try:
            rows = self.media_manager.db.fetchall("""
                SELECT id, blacklisted_at, procedure_code
                FROM media_items
                WHERE blacklist_flag = 1
            """)

            for row in rows:
                start = datetime.fromisoformat(row["blacklisted_at"])
                expiry = self._expiry_date(start, row["procedure_code"])
                if expiry and datetime.now() > expiry:
                    self.blacklist_manager.set_blacklist(row["id"], False)

            self.refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Abgelaufene konnten nicht entfernt werden: {e}")

    def _remove_all(self):
        try:
            self.media_manager.db.execute("""
                UPDATE media_items
                SET blacklist_flag = 0,
                    blacklisted_at = NULL,
                    procedure_code = 0
                WHERE blacklist_flag = 1
            """)
            self.refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Blacklist konnte nicht geleert werden: {e}")

class MediaDetailView(QWidget):
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
        desc = QLabel(item.description or "Keine Beschreibung verfügbar.")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Metadaten
        meta = QLabel(
            f"Typ: {item.type}\n"
            f"Provider: {item.source}\n"
            f"Provider-ID: {item.provider_id}\n"
            f"Erstellt am: {item.created_at}\n"
            f"Zuletzt geöffnet: {item.last_opened_at}\n"
            f"Öffnungsmethode: {item.open_method or '-'}"
        )
        layout.addWidget(meta)

        # Buttons
        btn_row = QHBoxLayout()

        open_btn = QPushButton("Öffnen")
        open_btn.clicked.connect(self.open_item)
        btn_row.addWidget(open_btn)

        fav_btn = QPushButton("Favorit" if not item.is_favorite else "Favorit entfernen")
        fav_btn.clicked.connect(self.toggle_favorite)
        btn_row.addWidget(fav_btn)

        back_btn = QPushButton("Zurück")
        back_btn.clicked.connect(self.back_callback)
        btn_row.addWidget(back_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def open_item(self):
        try:
            from core import OpenHandler
            handler = OpenHandler(self.media_manager)
            handler.open_item(self.item)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Konnte Medium nicht oeffnen: {e}")

    def toggle_favorite(self):
        try:
            new_value = 0 if self.item.is_favorite else 1
            self.media_manager.db.execute(
                "UPDATE media_items SET is_favorite = ? WHERE id = ?",
                (new_value, self.item.id)
            )
            notify_gui_refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"Favorit konnte nicht geaendert werden: {e}")
# ============================================================
# 8. MainWindow mit Sidebar
# ============================================================

class MainWindow(QMainWindow):
    def __init__(self, media_manager: MediaManager, blacklist_manager: BlacklistManager):
        super().__init__()

        self.media_manager = media_manager
        self.blacklist_manager = blacklist_manager

        self.setWindowTitle("MediaBrain")
        self.resize(
            config.config.get("ui.window_width", 1200),
            config.config.get("ui.window_height", 800)
        )

        # Hauptlayout: Sidebar + Content
        splitter = QSplitter()
        self.setCentralWidget(splitter)

        # Sidebar
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar.setLayout(sidebar_layout)
        sidebar.setObjectName("Sidebar") # Für CSS Styling

        btn_dash = QPushButton("Übersicht")
        btn_dash.clicked.connect(lambda: self.stack.setCurrentWidget(self.dashboard))
        sidebar_layout.addWidget(btn_dash)

        btn_movies = QPushButton("Filme")
        btn_movies.clicked.connect(lambda: self.stack.setCurrentWidget(self.library_movies))
        sidebar_layout.addWidget(btn_movies)

        btn_series = QPushButton("Serien")
        btn_series.clicked.connect(lambda: self.stack.setCurrentWidget(self.library_series))
        sidebar_layout.addWidget(btn_series)

        btn_music = QPushButton("Musik")
        btn_music.clicked.connect(lambda: self.stack.setCurrentWidget(self.library_music))
        sidebar_layout.addWidget(btn_music)

        btn_clips = QPushButton("Clips")
        btn_clips.clicked.connect(lambda: self.stack.setCurrentWidget(self.library_clips))
        sidebar_layout.addWidget(btn_clips)

        btn_favs = QPushButton("Favoriten")
        btn_favs.clicked.connect(lambda: self.stack.setCurrentWidget(self.favorites))
        sidebar_layout.addWidget(btn_favs)

        btn_blacklist = QPushButton("Blacklist")
        btn_blacklist.clicked.connect(lambda: self.stack.setCurrentWidget(self.blacklist_view))
        sidebar_layout.addWidget(btn_blacklist)

        btn_settings = QPushButton("Einstellungen")
        btn_settings.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(btn_settings)

        sidebar_layout.addStretch()

        splitter.addWidget(sidebar)

        # Content Stack
        self.stack = QStackedWidget()
        splitter.addWidget(self.stack)

        # --- Views Initialisieren ---

        # 1. Dashboard (Korrigiert: Echte View statt QLabel)
        self.dashboard = DashboardView(
            media_manager, 
            blacklist_manager,
            open_settings_callback=self.open_settings,
            open_blacklist_callback=lambda: self.stack.setCurrentWidget(self.blacklist_view)
        )
        self.stack.addWidget(self.dashboard)

        # 2. Libraries
        self.library_movies = LibraryView("movie", media_manager, blacklist_manager)
        self.stack.addWidget(self.library_movies)

        self.library_series = LibraryView("series", media_manager, blacklist_manager)
        self.stack.addWidget(self.library_series)

        self.library_music = LibraryView("music", media_manager, blacklist_manager)
        self.stack.addWidget(self.library_music)

        self.library_clips = LibraryView("clip", media_manager, blacklist_manager)
        self.stack.addWidget(self.library_clips)

        # 3. Favoriten
        self.favorites = FavoritesView(media_manager, blacklist_manager)
        self.stack.addWidget(self.favorites)

        # 4. Blacklist (Korrigiert: Echte View statt QLabel)
        self.blacklist_view = BlacklistView(media_manager, blacklist_manager)
        self.stack.addWidget(self.blacklist_view)

        # 5. Suche
        self.global_search = GlobalSearchView(media_manager, blacklist_manager)
        self.stack.addWidget(self.global_search)
        
        # Theme anwenden
        self.apply_theme()
        
        # Detail View Platzhalter
        self.detail_view = None

    def open_detail(self, item):
        self.detail_view = MediaDetailView(
            item,
            self.media_manager,
            self.blacklist_manager,
            back_callback=lambda: self.stack.setCurrentWidget(self.dashboard) # Oder letzte View
        )
        self.stack.addWidget(self.detail_view)
        self.stack.setCurrentWidget(self.detail_view)
           
    def refresh_all_views(self):
        """Aktualisiert alle Views - mit Error-Handling für Robustheit."""
        try:
            # Ruft jetzt die echten refresh() Methoden auf
            if hasattr(self.dashboard, 'refresh'): self.dashboard.refresh()
            if hasattr(self.library_movies, 'refresh'): self.library_movies.refresh()
            if hasattr(self.library_series, 'refresh'): self.library_series.refresh()
            if hasattr(self.library_music, 'refresh'): self.library_music.refresh()
            if hasattr(self.library_clips, 'refresh'): self.library_clips.refresh()
            if hasattr(self.favorites, 'refresh'): self.favorites.refresh()
            if hasattr(self.blacklist_view, 'refresh'): self.blacklist_view.refresh()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Fehler", f"GUI konnte nicht vollständig aktualisiert werden: {e}")

    def open_settings(self):
        self.settings_window = SettingsWindow()
        self.settings_window.show()
    
    def apply_theme(self):
        theme = config.config.get("ui.theme", "light")
        # Pfad ggf. anpassen, falls gui_resources nicht existiert
        try:
            path = Path(__file__).resolve().parent / "gui_resources" / ("styles_dark.qss" if theme == "dark" else "styles.qss")
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
        except Exception:
            pass