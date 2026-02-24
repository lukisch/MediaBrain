# MediaBrain – Architekturdiagramm

```mermaid
flowchart TD

    %% ===========================
    %% LAYER 1: GUI
    %% ===========================

    subgraph GUI["GUI Layer (PyQt6)"]
        Dashboard["Dashboard"]
        Libraries["Bibliotheken"]
        Favorites["Favoriten"]
        BlacklistView["Blacklist-Verwaltung"]
        DetailView["Detailseite"]
        Settings["Einstellungen"]
    end

    %% ===========================
    %% LAYER 2: CORE
    %% ===========================

    subgraph CORE["Core Layer"]
        DB["SQLite Database"]
        MediaManager["MediaManager"]
        BlacklistManager["BlacklistManager"]
        EventProcessor["EventProcessor (MainThread)"]
    end

    %% ===========================
    %% LAYER 3: PROVIDERS
    %% ===========================

    subgraph PROVIDERS["Provider Layer"]
        Netflix["NetflixProvider"]
        YouTube["YouTubeProvider"]
        Spotify["SpotifyProvider"]
        Local["LocalProvider"]
        ProviderRegistry["ProviderRegistry"]
    end

    %% ===========================
    %% LAYER 4: BACKGROUND
    %% ===========================

    subgraph BG["Background Layer (Threads)"]
        FileIndexer["FileIndexer"]
        BrowserWatcher["BrowserWatcher"]
        AppWatcher["AppWatcher"]
        TrayApp["TrayApp"]
        Queue["Thread-Safe Event Queue"]
    end

    %% ===========================
    %% CONNECTIONS
    %% ===========================

    %% GUI <-> CORE
    Dashboard --> MediaManager
    Libraries --> MediaManager
    Favorites --> MediaManager
    BlacklistView --> BlacklistManager
    DetailView --> MediaManager
    Settings --> CORE

    %% CORE <-> DB
    MediaManager --> DB
    BlacklistManager --> DB

    %% PROVIDERS <-> CORE
    ProviderRegistry --> MediaManager
    ProviderRegistry --> EventProcessor

    %% BACKGROUND -> CORE
    FileIndexer --> Queue
    BrowserWatcher --> Queue
    AppWatcher --> Queue
    TrayApp --> Queue

    Queue --> EventProcessor
