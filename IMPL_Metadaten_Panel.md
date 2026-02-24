# IMPLEMENTIERUNG: MediaBrain Metadaten im Detail-Panel

## Status: ANALYSE ABGESCHLOSSEN - BEREIT ZUR UMSETZUNG

**Datum:** 2026-01-12
**Aufgabe:** GUI - Metadaten im Detail-Panel anzeigen

---

## Analyse-Ergebnis

### Aktuelle Situation

Die `MediaDetailView` Klasse (gui.py, Zeile 1010-1081) zeigt nur lokale Basis-Metadaten:
- Titel, Beschreibung
- Typ, Provider, Provider-ID
- Erstellungs- und Oeffnungsdatum

### Was fehlt

Online-Metadaten von TMDb/OMDb/MusicBrainz werden NICHT angezeigt:
- Bewertung (Rating)
- Jahr
- Genres
- Laufzeit
- Regie
- Online-Beschreibung

### Loesung

Die `metadata_v2.py` hat bereits einen funktionierenden `MetadataFetcher` mit `auto_fetch()` Methode.
Dieser muss in die `MediaDetailView` integriert werden.

---

## Implementation (Manuell durchzufuehren)

### Schritt 1: Import hinzufuegen

Am Anfang von gui.py nach "from pathlib import Path":
```python
from threading import Thread
```

### Schritt 2: MediaDetailView erweitern (Zeile 1010-1081)

**A) Nach "# Metadaten" Block (ca. Zeile 1043):**

```python
        # === ONLINE METADATEN (dynamisch) ===
        online_label = QLabel("Online Metadaten:")
        online_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        layout.addWidget(online_label)
        
        self.online_meta_container = QVBoxLayout()
        self.online_meta_label = QLabel("Lade Online-Metadaten...")
        self.online_meta_label.setStyleSheet("padding-left: 10px; color: #888;")
        self.online_meta_container.addWidget(self.online_meta_label)
        layout.addLayout(self.online_meta_container)
        
        # Online-Metadaten laden
        self._load_online_metadata()
```

**B) Neue Methoden am Ende der Klasse hinzufuegen (vor class MainWindow):**

```python
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
        if result.get("title"): lines.append(f"  Titel: {result['title']}")
        if result.get("year"): lines.append(f"  Jahr: {result['year']}")
        if result.get("rating"): lines.append(f"  Bewertung: {result['rating']}/10")
        if result.get("genres"):
            genres = result['genres']
            if isinstance(genres, list): genres = ', '.join(genres)
            lines.append(f"  Genres: {genres}")
        if result.get("runtime"): lines.append(f"  Laufzeit: {result['runtime']} Min")
        if result.get("director"): lines.append(f"  Regie: {result['director']}")
        if result.get("source"): lines.append(f"  Quelle: {result['source']}")
        
        if lines:
            meta_text = "\\n".join(lines)
            label = QLabel(meta_text)
            label.setStyleSheet("padding-left: 10px; font-family: monospace;")
            self.online_meta_container.addWidget(label)
```

---

## Zeitaufwand fuer restliche Umsetzung

- Manuelles Patching: ~5 Min
- Test mit laufender GUI: ~3 Min
- Gesamt: ~8 Min

---

## Patch-Script vorhanden

Ein automatisches Patch-Script wurde erstellt, aber wegen Encoding-Risiken (siehe LESSONS_LEARNED) ist manuelles Patching empfohlen:

`patch_metadata_panel.py` - NICHT ohne manuelle Pruefung ausfuehren!

---
