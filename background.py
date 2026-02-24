"""
background.py
Hintergrundprozesse:
- WindowWatcher (erkennt aktives Fenster / Titel)
- FileIndexer (scannt lokale Dateien)
- TrayApp (Systemtray)
"""
import threading
import time
import traceback
import sys
import ctypes
from pathlib import Path
from providers import ProviderRegistry
import config
from logger_system import logger

# ============================================================
# Konstanten
# ============================================================
WINDOW_WATCHER_POLL_INTERVAL = 2    # Sekunden - WindowWatcher Polling-Frequenz
FILE_INDEXER_SCAN_INTERVAL = 60     # Sekunden - FileIndexer Full-Scan-Frequenz
TRAY_APP_SLEEP_INTERVAL = 10        # Sekunden - TrayApp Dummy-Loop (Placeholder)

# --- Hilfsfunktion: Aktives Fenster auslesen (Windows) ---
def get_active_window_title():
    """
    Liest den Titel des aktuell aktiven Fensters aus (nur Windows).

    Returns:
        str: Fenstertitel des aktiven Fensters, oder "" wenn nicht Windows
    """
    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value
    return ""

# ============================================================
# 1. EventDispatcher (Unverändert)
# ============================================================
class EventDispatcher:
    """
    Dispatcher für Media Events.

    Identifiziert Medien via ProviderRegistry und leitet Events
    an den EventProcessor weiter (Queue-basiert).
    """
    def __init__(self, event_processor):
        self.event_processor = event_processor

    def dispatch(self, source_string, origin="external"):
        """
        Identifiziert und dispatched einen Media Event.

        Args:
            source_string: URL, Fenstertitel oder Dateipfad
            origin: Event-Quelle (z.B. "window_watcher", "file_indexer")
        """
        # Versuchen, den String einem Provider zuzuordnen
        info = ProviderRegistry.identify(source_string)
        if not info:
            return

        info["origin"] = origin
        self.event_processor.queue.put(info)


# ============================================================
# 2. WindowWatcher (NEU: Ersetzt BrowserWatcher & AppWatcher)
# ============================================================
class WindowWatcher(threading.Thread):
    """
    Überwacht den Titel des aktiven Fensters.
    Erkennt z.B. "YouTube", "Netflix" oder "VLC" im Titel.
    """
    def __init__(self, event_processor):
        super().__init__(daemon=True)
        self.dispatcher = EventDispatcher(event_processor)
        self.running = True
        self.last_title = ""

    def run(self):
        """
        Thread-Loop: Überwacht aktives Fenster und dispatched Titel-Änderungen.

        Prüft alle 2 Sekunden das aktive Fenster und dispatched den Titel
        nur wenn er sich geändert hat (verhindert Duplikate).
        """
        while self.running:
            try:
                title = get_active_window_title()

                # Nur verarbeiten, wenn sich der Titel geändert hat und nicht leer ist
                if title and title != self.last_title:
                    self.last_title = title

                    #Debug-Ausgabe (damit du siehst, was erkannt wird)
                    logger.debug(f"Fenster erkannt: {title}")

                    self.dispatcher.dispatch(title, origin="window_watcher")

            except Exception:
                logger.error(f"Unerwarteter Fehler im Hintergrund-Thread: {traceback.format_exc()}")

            # Alle 2 Sekunden prüfen reicht völlig
            time.sleep(WINDOW_WATCHER_POLL_INTERVAL)

    def stop(self):
        """Stoppt den WindowWatcher Thread."""
        self.running = False


# ============================================================
# 3. FileIndexer (Unverändert, nur gekürzt dargestellt)
# ============================================================
class FileIndexer(threading.Thread):
    """
    File Indexer für lokale Mediendateien.

    Scannt konfigurierte Ordner (watch_paths) rekursiv nach unterstützten
    Dateiformaten (mp3, mp4, mkv, avi, flac, wav, pdf, epub, m4b).

    Verwendet mtime-basiertes Incremental Scanning für Performance.
    Scannt alle 60 Sekunden.
    """
    def __init__(self, event_processor):
        super().__init__(daemon=True)
        self.dispatcher = EventDispatcher(event_processor)
        self.running = True
        self.watch_paths = [Path(p) for p in config.config.get("file_indexer.watch_paths", [])]
        self.known_files = set()

    def run(self):
        """
        Thread-Loop: Scannt Watch-Pfade alle 60 Sekunden.

        Ruft scan() auf und fängt Exceptions ab um Thread-Stabilität
        zu gewährleisten.
        """
        logger.info("FileIndexer gestartet.")
        while self.running:
            try:
                self.scan()
            except Exception:
                logger.error(f"Unerwarteter Fehler im Hintergrund-Thread: {traceback.format_exc()}")
            time.sleep(FILE_INDEXER_SCAN_INTERVAL)

    def scan(self):
        """Scannt alle Watch-Pfade mit mtime-Check (Incremental Scan)."""
        import os
        
        for folder_path in self.watch_paths:
            if not self.running: return
            if not folder_path.exists(): continue

            try:
                # Top-Level Scan
                self._scan_recursive(folder_path)
            except Exception as e:
                logger.error(f"Fehler beim Scan von {folder_path}: {e}")

    def _scan_recursive(self, path: Path):
        """Scannt einen Ordner rekursiv, prüft mtime zur Optimierung."""
        if not self.running: return

        try:
            # Schneller Check: Hat sich im Ordner was getan?
            # Hinweis: Manche Dateisysteme aktualisieren mtime nicht rekursiv,
            # daher ist dies ein Kompromiss für Performance.
            
            # Wir holen alle Items im aktuellen Ordner
            try:
                with os.scandir(path) as it:
                    for entry in it:
                        if not self.running: return
                        
                        if entry.is_file():
                            self._process_file(Path(entry.path))
                        elif entry.is_dir():
                            self._scan_recursive(Path(entry.path))
            except PermissionError:
                pass
                
        except Exception as e:
            logger.warning(f"Fehler beim rekursiven Scan von {path}: {e}")

    def _process_file(self, file: Path):
        """Verarbeitet eine einzelne Datei."""
        # Schnelle Filterung nach Extension
        if file.suffix.lower() in [".mp3", ".mp4", ".mkv", ".avi", ".flac", ".wav", ".pdf", ".epub", ".m4b"]:
            file_id = str(file.resolve())

            if file_id not in self.known_files:
                self.known_files.add(file_id)
                self.dispatcher.dispatch(file_id, origin="file_indexer")
                # KEIN Sleep mehr pro Datei für maximale Performance

    def stop(self):
        """Stoppt den FileIndexer Thread."""
        self.running = False


# ============================================================
# 4. TrayApp (Dummy bleibt vorerst)
# ============================================================
class TrayApp(threading.Thread):
    """
    System Tray Application (Placeholder).

    Aktuell nur ein Dummy-Thread.
    TODO: Tray-Icon, Kontext-Menu, Notifications implementieren.
    """
    def __init__(self, event_processor):
        super().__init__(daemon=True)
    def run(self):
        """Dummy run-Loop."""
        while True: time.sleep(TRAY_APP_SLEEP_INTERVAL)