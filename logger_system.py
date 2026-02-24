
import logging
import os
from pathlib import Path

# Log-Pfad sicherstellen
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "mediabrain.log"

def setup_logger(name="MediaBrain"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Verhindern, dass Handler mehrfach hinzugefügt werden (Singleton-ish)
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # File Handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Globale Instanz für einfachen Zugriff
logger = setup_logger()
