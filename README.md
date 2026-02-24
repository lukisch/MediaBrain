# MediaBrain

MediaBrain ist eine lokale, datenschutzfreundliche Medien‑Zentrale, die Inhalte aus *allen* Quellen automatisch erkennt, sammelt, organisiert und zugänglich macht.  
Sie vereint Streaming‑Dienste, lokale Dateien, Browser‑Aktivität und App‑Nutzung in einer einzigen, einheitlichen Oberfläche.

## 🎯 Zweck

Moderne Medien sind über viele Plattformen verstreut: Netflix, YouTube, Spotify, lokale Dateien, Browser‑Tabs, Apps.  
MediaBrain löst dieses Problem, indem es:

- Medien automatisch erkennt  
- Metadaten lokal speichert  
- eine einheitliche Oberfläche bietet  
- Inhalte intelligent öffnet (Browser, App, lokal)  
- Favoriten, Blacklist, Sortierung und Detailseiten bereitstellt  
- komplett offline und datenschutzfreundlich arbeitet  

## 🧩 Hauptfunktionen

### ✅ Medienerkennung
- Netflix‑Titel  
- YouTube‑Videos  
- Spotify‑Tracks  
- Lokale Dateien (mp3, mp4, mkv, pdf, epub …)

### ✅ Medienverwaltung
- Favoriten  
- Blacklist (mit Ablaufdatum)  
- Sortierung  
- Filter  
- Detailansicht  
- Chronik (erstellt, zuletzt geöffnet, Öffnungsmethode)

### ✅ Öffnen‑Logik
- Browser  
- App‑Deep‑Links  
- Lokale Dateien  
- Auto‑Modus (merkt sich letzte Methode)

### ✅ Datei‑Aktionen
- Im Explorer anzeigen  
- Datei löschen (optional)  
- Metadaten aktualisieren (Platzhalter)

### ✅ Dashboard
- Favoriten  
- Zuletzt geöffnet  
- Globale Suche  
- Statistiken  
- Quick Actions  

### ✅ Bibliotheken
- Filme  
- Serien  
- Musik  
- Clips  
- Podcasts  
- Hörbücher  
- Dokumente  

### ✅ Blacklist‑Verwaltung
- Filter (Provider, Dauer, Ablaufstatus)  
- Dauer ändern  
- Entfernen  
- Abgelaufene löschen  
- Alle löschen  

### ✅ Theme‑System
- Light Theme  
- Dark Theme  
- Dynamisches Umschalten  
- Speicherung in settings.json  

### ✅ Reaktives Refresh‑System
- Hintergrundprozesse → Queue → MainThread → GUI aktualisiert  

## 🏗️ Architektur

MediaBrain besteht aus vier Schichten:

- **Core Layer** (Database, MediaManager, BlacklistManager, EventProcessor)  
- **Provider Layer** (Netflix, YouTube, Spotify, Local)  
- **Background Layer** (FileIndexer, BrowserWatcher, AppWatcher, TrayApp)  
- **GUI Layer** (Dashboard, Bibliotheken, Favoriten, Blacklist, Einstellungen)

Ein vollständiges Architekturdiagramm findest du in `ARCHITEKTUR.md`.

## 🚀 Status

MediaBrain ist bereits voll funktionsfähig:

- Core vollständig  
- Provider vollständig  
- Datenbank vollständig  
- GUI vollständig  
- Öffnen‑Logik vollständig  
- Datei‑Aktionen implementiert  
- Sortierung implementiert  
- Detailseite implementiert  
- Refresh‑System implementiert  
- Thread‑Safety gewährleistet  

Offene Punkte findest du in der `ROADMAP.md`.

## 📄 Lizenz

Proprietär / intern (noch nicht festgelegt)
