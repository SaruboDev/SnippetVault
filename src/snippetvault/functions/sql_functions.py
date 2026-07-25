import sqlite3
from sqlite3 import Connection, Cursor

import typer

from rich import print
import os
import re
from pathlib import Path

from . import settings

class TableNameErr(Exception):
    pass

class DbNotExistent(Exception):
    pass

def check_table_security(name: str) -> bool:
    """
    Quick regex filter.
    """

    if not re.match("^[a-zA-Z0-9_]+$", name):
        raise TableNameErr("Table name not valid or unsafe!")
    return True

def create_database(name: str, db_path: Path|None = None) -> Connection:
    """
    Creates a new database and the tables required.    
    """
    if db_path is None:
        db_path = Path(settings.read_settings_file("database_path"))
    
    if not str(db_path).endswith("database.db"):
        full_path = db_path / "database.db"
    else:
        full_path = db_path

    connection: Connection = sqlite3.connect(full_path)
    cur: Cursor = connection.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    
    check_table_security(name)
    
    cur.execute(f"CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, timedate TEXT DEFAULT CURRENT_TIMESTAMP)")
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS "{name}_tags" (
            element_id INTEGER,
            tag TEXT,
            PRIMARY KEY (element_id, tag),
            FOREIGN KEY (element_id) REFERENCES "{name}"(id) ON DELETE CASCADE)
    """)

    connection.commit()

    return connection

def get_full_db_path(db_path: Path|None = None):
    if db_path is None:
        result = settings.read_settings_file("database_path")

        db_path = Path(result)
    
    db_path_full = db_path / "database.db"
    return db_path_full

def check_or_create_database(name: str, db_path: Path|None = None) -> bool:
    """
    Checks if the database already exists, otherwise, asks if it should create a new one.
    """
    db_path_full = get_full_db_path(db_path)
    check_table_security(name)

    if os.path.exists(db_path_full):
        connection = sqlite3.connect(db_path_full)
        cur = connection.cursor()
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table';")

        table_list = cur.fetchall()
        table_list_flat = [item[0] for item in table_list]

        if not name in table_list_flat:
            return False
        return True
    else:
        return False

def add_to_vault(
        vault_name: str,
        snippet_name: str,
        description: str,
        tags: list[str],
        db_path: Path|None = None
    ) -> None:
    """
    Adds new snippets to the vault.
    """
    if check_or_create_database(vault_name, db_path) == False:
        raise DbNotExistent("Database or table doesn't exists.")

    db_path = get_full_db_path(db_path)
    check_table_security(vault_name)
    
    if not db_path.exists():
        raise DbNotExistent("Database doesn't exists, try using the 'create-vault' command first.")

    connection: Connection = create_database(vault_name, db_path)

    cur: Cursor = connection.cursor()

    cur.execute(f"INSERT INTO {vault_name} (name, description) VALUES(?, ?)", (snippet_name, description))
    last_id = cur.lastrowid

    for tag in tags:
        cur.execute(
            f"INSERT OR IGNORE INTO '{vault_name}_tags' (element_id, tag) VALUES (?, ?)", (last_id, tag)
        )

    connection.commit()
    connection.close()
    return

def search_in_vault(
        vault_name: str,
        snippet_or_tag: str,
        is_tag: bool = False,
        db_path: Path|None = None
):
    check_or_create_database(vault_name, db_path)

    db_path = get_full_db_path(db_path)
    check_table_security(vault_name)

    if not db_path.exists():
        raise DbNotExistent("Database doesn't exists, try using the 'create-vault' command first.")

    if not is_tag:
        connection: Connection = create_database(vault_name, db_path)
        
        cur: Cursor = connection.cursor()

        cur.execute(f"""
        SELECT t.name, t.description, ts.tag FROM "{vault_name}" AS t
        LEFT JOIN "{vault_name}_tags" AS ts ON t.id = ts.element_id
        WHERE t.name = ?;
        """, (snippet_or_tag, )
        )
        results = cur.fetchall()

        connection.close()

        return results

    # Else, they're searching by tags

    connection: Connection = create_database(vault_name, db_path)
    
    cur: Cursor = connection.cursor()

    cur.execute(f"""
    SELECT t.name, t.description, ts.tag FROM '{vault_name}' AS t
    LEFT JOIN {vault_name}_tags AS ts ON t.id = ts.element_id
    WHERE ts.tag = ?;
    """, (snippet_or_tag, )
    )
    results = cur.fetchall()

    connection.close()

    return results