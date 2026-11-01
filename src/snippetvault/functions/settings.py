from tomlkit import parse
from tomlkit import table
from tomlkit import dumps
from tomlkit import document
from tomlkit import TOMLDocument

import platform
import os
from pathlib import Path

from typing import Any

class KeyNameErr(Exception):
    pass

class SettingsNoExists(Exception):
    pass

class OSCheckErr(Exception):
    pass

class GeneralSettingsErr(Exception):
    pass

def check_os() -> Path:
    """
    Checks system's os and returns the config path.
    """

    os_type: str = platform.system().lower()
    file_path: Path

    match os_type:
        case "linux":
            file_path = Path.home() / ".config/snippetvault/"
        case "darwin":
            file_path = Path.home() / "Library/Application Support/snippetvault/"
        case "windows":
            file_path = Path(os.path.expandvars("%APPDATA%")) / "snippetvault/"
        case _:
            file_path = Path.home() / ".snippetvault/"
    return file_path

def create_settings_file(
        file_path: Path,
        db_path: Path|None = None
    ) -> None:
    """
    Simply creates a new settings file.
    """

    file_path.parent.mkdir(parents=True, exist_ok = True)
    
    doc = document()

    if db_path is None:
        db_path = Path().home() / "documents"

    general = table()
    general["database_path"] = str(db_path)
    doc.add("general", general)

    file_path.write_text(dumps(doc), encoding = "utf-8")

    return

def check_settings_file(file_path: Path|None = None, db_path: Path|None = None) -> bool:
    """
    Checks if a settings file exists or should create a new one.
    """
    if file_path is None:
        try:
            file_path = check_os()
        except Exception as e:
            raise OSCheckErr(f"An error occurred while checking os type. {e}") from e

    file_path_settings = file_path / "config.toml"

    if file_path_settings.exists():
        return True
    
    try:
        create_settings_file(file_path_settings, db_path)

    except OSError as e:
        raise GeneralSettingsErr(f"Error occurred while generating new settings file. {e}") from e
    return True

def read_settings_file(key_name: str | None, file_path: Path|None = None, db_path: Path| None = None) -> str|bool:
    """
    Reads a specific key from the settings, if no key was given, gives the whole settings.
    """
    
    if file_path is None:
        file_path = check_os()

    if not check_settings_file(file_path, db_path):
        return False
    
    file_path_settings = file_path / "config.toml"

    if key_name is None:
        return file_path_settings.read_text(encoding = "utf-8")
    
    doc = parse(file_path_settings.read_text(encoding = "utf-8"))

    result = ""

    match key_name:
        case "database_path":
            result = Path(doc["general"]["database_path"])
        case _:
            return file_path_settings.read_text(encoding = "utf-8")

    return result

def change_settings(value: Any, key_name: str|None = None, file_path: Path|None = None, db_path: Path|None = None) -> bool:
    """
    Changes any specified settings from the settings file.
    """
    if key_name is None:
        raise KeyNameErr("Gotta specify a setting to change!")
    
    if file_path is None:
        try:
            file_path: Path = check_os()
        except Exception as e:
            raise OSCheckErr(f"Something went wrong while checking os type. {e}") from e

    if not check_settings_file(file_path, db_path):
        raise SettingsNoExists("Settings doesn't exists. If you see this, congrats, because i don't know why.")

    file_path_settings = file_path / "config.toml"

    doc = parse(file_path_settings.read_text(encoding = "utf-8"))

    old_path: Path|None = None
    if key_name == "database_path":
        old_path = Path(doc["general"]["database_path"])
        doc["general"]["database_path"] = str(value)
    ## NOTE: Add new keys if necessary.

    file_path_settings.write_text(dumps(doc), encoding = "utf-8")

    if old_path is not None:
        if (old_path / "snippetvault.db").exists():
            try:
                old_path_complete: Path = old_path / "snippetvault.db"
                new_path_complete: Path = Path(value) / "snippetvault.db"
                new_path_complete.parent.mkdir(parents=True, exist_ok=True)
                old_path_complete.replace(new_path_complete)

            except OSError as e:
                raise Exception(f"Exception while moving settings location! {e}") from e
    return True