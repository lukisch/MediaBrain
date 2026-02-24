"""
search_advanced.py
Erweiterte Suchfunktionalität für MediaBrain.
- Filter nach Typ, Provider, Zeitraum
- Sortierung (Titel, Datum, Rating)
- Tag-System
- Speicherbare Suchprofile

Version: 1.0
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QFrame, QGroupBox,
    QDateEdit, QSpinBox, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QFormLayout, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QStringListModel
from PyQt6.QtGui import QIcon

from datetime import datetime, timedelta
import json
from pathlib import Path

# ============================================================
# 1. Filter-Definitionen
# ============================================================

MEDIA_TYPES = [
    ("Alle", None),
    ("Filme", "movie"),
    ("Serien", "series"),
    ("Musik", "music"),
    ("Clips", "clip"),
    ("Podcasts", "podcast"),
    ("Hörbücher", "audiobook"),
    ("Dokumente", "document")
]

PROVIDERS = [
    ("Alle", None),
    ("Netflix", "netflix"),
    ("Disney+", "disney"),
    ("Amazon Prime", "prime"),
    ("Apple TV+", "appletv"),
    ("YouTube", "youtube"),
    ("Twitch", "twitch"),
    ("Spotify", "spotify"),
    ("Lokal", "local")
]

SORT_OPTIONS = [
    ("Zuletzt geöffnet", "last_opened_at", True),
    ("Titel A-Z", "title", False),
    ("Titel Z-A", "title", True),
    ("Hinzugefügt (neu)", "created_at", True),
    ("Hinzugefügt (alt)", "created_at", False),
    ("Bewertung", "rating", True)
]

TIME_FILTERS = [
    ("Alle Zeiten", None),
    ("Heute", 1),
    ("Letzte 7 Tage", 7),
    ("Letzte 30 Tage", 30),
    ("Letzte 90 Tage", 90),
    ("Dieses Jahr", 365)
]

# ============================================================
# 2. SearchCriteria Datenklasse
# ============================================================

class SearchCriteria:
    """Hält alle Suchkriterien."""
    
    def __init__(self):
        self.text = ""
        self.media_type = None
        self.provider = None
        self.favorites_only = False
        self.exclude_blacklist = True
        self.time_filter_days = None
        self.sort_field = "last_opened_at"
        self.sort_desc = True
        self.tags = []
        self.min_rating = None
        
    def to_dict(self):
        return {
            "text": self.text,
            "media_type": self.media_type,
            "provider": self.provider,
            "favorites_only": self.favorites_only,
            "exclude_blacklist": self.exclude_blacklist,
            "time_filter_days": self.time_filter_days,
            "sort_field": self.sort_field,
            "sort_desc": self.sort_desc,
            "tags": self.tags,
            "min_rating": self.min_rating
        }
    
    @classmethod
    def from_dict(cls, data):
        c = cls()
        c.text = data.get("text", "")
        c.media_type = data.get("media_type")
        c.provider = data.get("provider")
        c.favorites_only = data.get("favorites_only", False)
        c.exclude_blacklist = data.get("exclude_blacklist", True)
        c.time_filter_days = data.get("time_filter_days")
        c.sort_field = data.get("sort_field", "last_opened_at")
        c.sort_desc = data.get("sort_desc", True)
        c.tags = data.get("tags", [])
        c.min_rating = data.get("min_rating")
        return c

# ============================================================
# 3. AdvancedSearchBar Widget
# ============================================================

class AdvancedSearchBar(QWidget):
    """
    Erweiterte Suchleiste mit:
    - Textsuche mit Autocomplete
    - Quick-Filter Buttons
    - Erweiterbare Filter-Optionen
    """
    
    search_triggered = pyqtSignal(SearchCriteria)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.criteria = SearchCriteria()
        self.is_expanded = False
        self._setup_ui()
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # === Hauptzeile: Suchfeld + Buttons ===
        search_row = QHBoxLayout()
        
        # Suchfeld
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Suchen... (Titel, Beschreibung, Tags)")
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._trigger_search)
        search_row.addWidget(self.search_input, stretch=1)
        
        # Quick-Filter Buttons
        self.btn_favorites = QPushButton("⭐")
        self.btn_favorites.setCheckable(True)
        self.btn_favorites.setToolTip("Nur Favoriten")
        self.btn_favorites.setFixedWidth(40)
        self.btn_favorites.toggled.connect(self._on_favorites_toggle)
        search_row.addWidget(self.btn_favorites)
        
        # Typ-Filter Dropdown
        self.combo_type = QComboBox()
        self.combo_type.setFixedWidth(100)
        for label, value in MEDIA_TYPES:
            self.combo_type.addItem(label, value)
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        search_row.addWidget(self.combo_type)
        
        # Provider-Filter Dropdown
        self.combo_provider = QComboBox()
        self.combo_provider.setFixedWidth(120)
        for label, value in PROVIDERS:
            self.combo_provider.addItem(label, value)
        self.combo_provider.currentIndexChanged.connect(self._on_provider_changed)
        search_row.addWidget(self.combo_provider)
        
        # Erweitert-Button
        self.btn_expand = QPushButton("▼")
        self.btn_expand.setFixedWidth(30)
        self.btn_expand.setToolTip("Erweiterte Filter")
        self.btn_expand.clicked.connect(self._toggle_expand)
        search_row.addWidget(self.btn_expand)
        
        # Reset-Button
        self.btn_reset = QPushButton("✕")
        self.btn_reset.setFixedWidth(30)
        self.btn_reset.setToolTip("Filter zurücksetzen")
        self.btn_reset.clicked.connect(self.reset_filters)
        search_row.addWidget(self.btn_reset)
        
        main_layout.addLayout(search_row)
        
        # === Erweiterte Filter (ausklappbar) ===
        self.filter_panel = QFrame()
        self.filter_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        self.filter_panel.setVisible(False)
        
        filter_layout = QHBoxLayout(self.filter_panel)
        
        # Zeitraum
        time_group = QGroupBox("Zeitraum")
        time_layout = QVBoxLayout(time_group)
        self.combo_time = QComboBox()
        for label, value in TIME_FILTERS:
            self.combo_time.addItem(label, value)
        self.combo_time.currentIndexChanged.connect(self._on_time_changed)
        time_layout.addWidget(self.combo_time)
        filter_layout.addWidget(time_group)
        
        # Sortierung
        sort_group = QGroupBox("Sortierung")
        sort_layout = QVBoxLayout(sort_group)
        self.combo_sort = QComboBox()
        for label, field, desc in SORT_OPTIONS:
            self.combo_sort.addItem(label, (field, desc))
        self.combo_sort.currentIndexChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(self.combo_sort)
        filter_layout.addWidget(sort_group)
        
        # Optionen
        options_group = QGroupBox("Optionen")
        options_layout = QVBoxLayout(options_group)
        
        self.chk_blacklist = QCheckBox("Blacklist ausblenden")
        self.chk_blacklist.setChecked(True)
        self.chk_blacklist.toggled.connect(self._on_blacklist_toggle)
        options_layout.addWidget(self.chk_blacklist)
        
        self.chk_local_only = QCheckBox("Nur lokale Dateien")
        self.chk_local_only.toggled.connect(self._trigger_search)
        options_layout.addWidget(self.chk_local_only)
        
        filter_layout.addWidget(options_group)
        
        # Tags
        tags_group = QGroupBox("Tags")
        tags_layout = QVBoxLayout(tags_group)
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("Tag hinzufügen...")
        self.tag_input.returnPressed.connect(self._add_tag)
        tags_layout.addWidget(self.tag_input)
        
        self.tag_list = QLabel("")
        self.tag_list.setWordWrap(True)
        tags_layout.addWidget(self.tag_list)
        filter_layout.addWidget(tags_group)
        
        main_layout.addWidget(self.filter_panel)
        
    def _toggle_expand(self):
        self.is_expanded = not self.is_expanded
        self.filter_panel.setVisible(self.is_expanded)
        self.btn_expand.setText("▲" if self.is_expanded else "▼")
        
    def _on_text_changed(self, text):
        self.criteria.text = text
        self._trigger_search()
        
    def _on_type_changed(self, index):
        self.criteria.media_type = self.combo_type.currentData()
        self._trigger_search()
        
    def _on_provider_changed(self, index):
        self.criteria.provider = self.combo_provider.currentData()
        self._trigger_search()
        
    def _on_favorites_toggle(self, checked):
        self.criteria.favorites_only = checked
        self._trigger_search()
        
    def _on_time_changed(self, index):
        self.criteria.time_filter_days = self.combo_time.currentData()
        self._trigger_search()
        
    def _on_sort_changed(self, index):
        data = self.combo_sort.currentData()
        if data:
            self.criteria.sort_field, self.criteria.sort_desc = data
        self._trigger_search()
        
    def _on_blacklist_toggle(self, checked):
        self.criteria.exclude_blacklist = checked
        self._trigger_search()
        
    def _add_tag(self):
        tag = self.tag_input.text().strip()
        if tag and tag not in self.criteria.tags:
            self.criteria.tags.append(tag)
            self._update_tag_display()
            self.tag_input.clear()
            self._trigger_search()
            
    def _update_tag_display(self):
        if self.criteria.tags:
            self.tag_list.setText("Tags: " + ", ".join(f"[{t}]" for t in self.criteria.tags))
        else:
            self.tag_list.setText("")
            
    def _trigger_search(self):
        self.search_triggered.emit(self.criteria)
        
    def reset_filters(self):
        """Setzt alle Filter zurück."""
        self.criteria = SearchCriteria()
        self.search_input.clear()
        self.btn_favorites.setChecked(False)
        self.combo_type.setCurrentIndex(0)
        self.combo_provider.setCurrentIndex(0)
        self.combo_time.setCurrentIndex(0)
        self.combo_sort.setCurrentIndex(0)
        self.chk_blacklist.setChecked(True)
        self.chk_local_only.setChecked(False)
        self.criteria.tags.clear()
        self._update_tag_display()
        self._trigger_search()
        
    def get_criteria(self):
        return self.criteria

# ============================================================
# 4. SearchEngine
# ============================================================

class SearchEngine:
    """
    Führt erweiterte Suchen auf der Datenbank aus.
    """
    
    def __init__(self, db):
        self.db = db
        
    def search(self, criteria: SearchCriteria):
        """Führt Suche basierend auf Kriterien aus."""
        
        # Basis-Query
        query = "SELECT * FROM media_items WHERE 1=1"
        params = []
        
        # Textsuche
        if criteria.text:
            query += " AND (title LIKE ? OR description LIKE ?)"
            search_term = f"%{criteria.text}%"
            params.extend([search_term, search_term])
        
        # Typ-Filter
        if criteria.media_type:
            query += " AND type = ?"
            params.append(criteria.media_type)
        
        # Provider-Filter
        if criteria.provider:
            query += " AND source = ?"
            params.append(criteria.provider)
        
        # Favoriten
        if criteria.favorites_only:
            query += " AND is_favorite = 1"
        
        # Blacklist
        if criteria.exclude_blacklist:
            query += " AND blacklist_flag = 0"
        
        # Zeitraum
        if criteria.time_filter_days:
            cutoff = (datetime.now() - timedelta(days=criteria.time_filter_days)).isoformat()
            query += " AND last_opened_at >= ?"
            params.append(cutoff)
        
        # Sortierung
        order_dir = "DESC" if criteria.sort_desc else "ASC"
        query += f" ORDER BY {criteria.sort_field} {order_dir}"
        
        # Limit
        query += " LIMIT 500"
        
        # Ausführen
        rows = self.db.fetchall(query, params)
        
        # In MediaItem-Objekte umwandeln
        from core import MediaItem
        return [MediaItem(row) for row in rows]
    
    def get_suggestions(self, text, limit=10):
        """Holt Vorschläge für Autocomplete."""
        if not text or len(text) < 2:
            return []
        
        query = """
            SELECT DISTINCT title FROM media_items 
            WHERE title LIKE ? AND blacklist_flag = 0
            ORDER BY last_opened_at DESC
            LIMIT ?
        """
        rows = self.db.fetchall(query, (f"%{text}%", limit))
        return [row["title"] for row in rows]
    
    def get_all_tags(self):
        """Holt alle verwendeten Tags (für Autocomplete)."""
        # Placeholder - Tags müssten in der DB gespeichert werden
        return []

# ============================================================
# 5. SearchProfileManager
# ============================================================

class SearchProfileManager:
    """Verwaltet gespeicherte Suchprofile."""
    
    def __init__(self, config_path=None):
        self.config_path = config_path or Path.home() / ".mediabrain" / "search_profiles.json"
        self.profiles = {}
        self._load()
        
    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, criteria_dict in data.items():
                        self.profiles[name] = SearchCriteria.from_dict(criteria_dict)
            except:
                pass
                
    def _save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            data = {name: criteria.to_dict() for name, criteria in self.profiles.items()}
            json.dump(data, f, indent=2)
            
    def save_profile(self, name, criteria):
        self.profiles[name] = criteria
        self._save()
        
    def load_profile(self, name):
        return self.profiles.get(name)
        
    def delete_profile(self, name):
        if name in self.profiles:
            del self.profiles[name]
            self._save()
            
    def list_profiles(self):
        return list(self.profiles.keys())

# ============================================================
# 6. SaveSearchDialog
# ============================================================

class SaveSearchDialog(QDialog):
    """Dialog zum Speichern einer Suche als Profil."""
    
    def __init__(self, criteria, parent=None):
        super().__init__(parent)
        self.criteria = criteria
        self.setWindowTitle("Suche speichern")
        self.setMinimumWidth(300)
        
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name für diese Suche...")
        layout.addRow("Name:", self.name_input)
        
        # Zusammenfassung
        summary = self._build_summary()
        summary_label = QLabel(summary)
        summary_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addRow("Filter:", summary_label)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
    def _build_summary(self):
        parts = []
        if self.criteria.text:
            parts.append(f'Text: "{self.criteria.text}"')
        if self.criteria.media_type:
            parts.append(f"Typ: {self.criteria.media_type}")
        if self.criteria.provider:
            parts.append(f"Provider: {self.criteria.provider}")
        if self.criteria.favorites_only:
            parts.append("Nur Favoriten")
        return ", ".join(parts) if parts else "Keine Filter"
        
    def get_name(self):
        return self.name_input.text().strip()
