import sys
import os
import time

# Add current dir to path to import config
sys.path.append(os.getcwd())

from config import Config, SETTINGS_PATH

def test_safe_config():
    print("--- START Config Safety Test ---")
    
    # Clean state
    if SETTINGS_PATH.exists():
        try: os.remove(SETTINGS_PATH)
        except: pass
    backup_path = SETTINGS_PATH.with_suffix(".json.bak")
    if backup_path.exists():
        try: os.remove(backup_path)
        except: pass

    # 1. Init Config (creates defaults)
    conf = Config()
    conf.set("ui.theme", "test_theme")
    print(f"1. Init & Save: theme={conf.get('ui.theme')}")
    
    # 2. Modify & Save (should create Backup)
    conf.set("ui.theme", "new_theme")
    print(f"2. Modify & Save: theme={conf.get('ui.theme')}")
    
    if not backup_path.exists():
        print("FAIL: No backup created")
        return
    else:
        print("PASS: Backup created")

    # 3. Corrupt settings.json
    with open(SETTINGS_PATH, "a") as f:
        f.write("GARBAGE DATA")
    print("3. Corrupted settings.json")

    # 4. Reload (Should trigger Recovery)
    print("4. Reloading Config...")
    conf2 = Config()
    val = conf2.get("ui.theme")
    
    # Expect 'test_theme' because backup contains state BEFORE last save
    if val == "test_theme": 
        print(f"PASS: Recovered value '{val}' from backup")
    elif val == "new_theme":
        print(f"WARN: Recovered CURRENT value (backup overwrote file?): {val}")
    elif val == "light":
        print(f"FAIL: Reset to defaults (Recovery failed)")
    else:
        print(f"ERROR: Unexpected value '{val}'")

    # Cleanup
    try:
        if SETTINGS_PATH.exists(): os.remove(SETTINGS_PATH)
        if backup_path.exists(): os.remove(backup_path)
    except: pass
    
    print("--- END Config Safety Test ---")

if __name__ == "__main__":
    test_safe_config()
