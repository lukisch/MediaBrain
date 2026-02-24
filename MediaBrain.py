"""
MediaBrain.py
Hauptstartpunkt der Anwendung.
Verbindet GUI, Datenbank und Hintergrundprozesse.
"""
import queue
import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer # Import nach oben verschoben

# Projektordner zum Pfad hinzufügen
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core import Database, MediaManager, BlacklistManager, EventProcessor
from gui import MainWindow
import background
import config
from logger_system import logger

class AppController:
    def __init__(self):
        logger.info("Starte MediaBrain...")
        
        # 1. Core Komponenten
        self.db = Database(config.DB_PATH)
        self.media_manager = MediaManager(self.db)
        self.blacklist_manager = BlacklistManager(self.db)

        # 2. Event Processor (Verbindung zwischen Background & GUI)
        self.event_processor = EventProcessor(self.media_manager)
        self.event_processor.queue = queue.Queue()

        # 3. GUI starten
        self.app = QApplication(sys.argv)
        self.window = MainWindow(self.media_manager, self.blacklist_manager)
        
        # GUI Refresh verbinden
        self.event_processor.on_data_changed = self.window.refresh_all_views

        # 4. Hintergrundprozesse starten
        self.background_services = []
        self._start_background_services()

        # 5. Event Loop starten (WICHTIG!)
        self._start_event_loop()

        self.window.show()
        logger.info("GUI gestartet. Warte auf Events...")

    # In MediaBrain.py -> AppController
    def _start_event_loop(self):
        """Prüft regelmäßig die Queue auf neue Daten."""
        
        def process_queue():
            processed_count = 0
            has_updates = False
            
            # Verarbeite maximal 50 Items pro Tick, damit die GUI nicht einfriert
            while not self.event_processor.queue.empty() and processed_count < 50:
                event = self.event_processor.queue.get()
                try:
                    self.event_processor.process_event(event)
                    has_updates = True
                except Exception as e:
                    logger.error(f"Fehler bei Event-Verarbeitung: {e}")
                
                processed_count += 1

            # Erst NACHDEM der Stapel (bis zu 50 Stück) durch ist: EINMAL refreshen
            if has_updates:
                # print(f"[GUI] Refresh ausgelöst für {processed_count} Items.")
                self.window.refresh_all_views()

        # Timer speichern, damit er aktiv bleibt
        self.timer = QTimer()
        self.timer.timeout.connect(process_queue)
        self.timer.start(200)  # Alle 200ms prüfen

    def _start_background_services(self):
        """Startet WindowWatcher, FileIndexer etc."""
        # WindowWatcher (Fenstertitel)
        try:
            win_watcher = background.WindowWatcher(self.event_processor)
            win_watcher.start()
            self.background_services.append(win_watcher)
        except Exception as e:
            logger.error(f"Fehler WindowWatcher: {e}")

        # File Indexer (Lokale Dateien)
        try:
            files = background.FileIndexer(self.event_processor)
            files.start()
            self.background_services.append(files)
        except Exception as e:
            logger.error(f"Fehler FileIndexer: {e}")

        # Tray (Optional)
        try:
            tray = background.TrayApp(self.event_processor)
            tray.start()
            self.background_services.append(tray)
        except Exception: 
            pass

    def notify_data_changed(self):
        """Benachrichtigt die GUI über Datenänderungen.

        Diese Methode wird von gui.py aufgerufen, wenn Daten geändert wurden
        (z.B. Favorit-Toggle, Blacklist, Datei löschen).
        """
        self.window.refresh_all_views()

    def run(self):
        """Startet die Qt-Eventloop."""
        sys.exit(self.app.exec())

# Globale Controller-Instanz (wird von gui.py importiert)
controller = None

if __name__ == "__main__":
    controller = AppController()
    controller.run()