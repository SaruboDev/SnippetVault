import sqlite3
from sqlite3 import Connection, Cursor
import os
import re
from pathlib import Path

from . import settings

class TableNameErr(Exception):
    pass

class DbNotExistent(Exception):
    pass

class NoOptions(Exception):
    pass

def check_table_security(name: str) -> bool:
    """
    Quick regex filter.
    """

    if not re.match("^[a-zA-Z0-9_]+$", name):
        raise TableNameErr("Table name not valid or unsafe!")
    return True

def connect_or_create_database(name: str, db_path: Path|None = None) -> Connection:
    """
    Creates a new database and the tables required or connects to an existing one.    
    """
    full_path = get_full_db_path(db_path)

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

    if not str(db_path).endswith("database.db"):
        db_path_full = db_path / "database.db"
    else:
        db_path_full = db_path

    return db_path_full

def database_exists(name: str, db_path: Path|None = None) -> bool:
    """
    Checks if the database already exists, otherwise, asks if it should create a new one.
    """
    db_path_full = get_full_db_path(db_path)
    check_table_security(name)

    if os.path.exists(db_path_full):
        connection = sqlite3.connect(db_path_full)
        cur = connection.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table';")

        table_list = cur.fetchall()
        table_list_flat = [item[0] for item in table_list]

        name_tags = name + "_tags"

        if not name in table_list_flat or not name_tags in table_list_flat:
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
    if database_exists(vault_name, db_path) == False:
        raise DbNotExistent("Database or table doesn't exists.")

    db_path = get_full_db_path(db_path)
    check_table_security(vault_name)
    
    if not db_path.exists():
        raise DbNotExistent("Database doesn't exists, try using the 'create-vault' command first.")

    connection: Connection = connect_or_create_database(vault_name, db_path)

    cur: Cursor = connection.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

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
    exists = database_exists(vault_name, db_path)
    if not exists:
        raise DbNotExistent("Database or Vault doesn't exist.")

    db_path = get_full_db_path(db_path)
    check_table_security(vault_name)

    if not db_path.exists():
        raise DbNotExistent("Database doesn't exists, try using the 'create-vault' command first.")

    if not is_tag:
        connection: Connection = connect_or_create_database(vault_name, db_path)
        
        cur: Cursor = connection.cursor()
        cur.execute("PRAGMA foreign_keys = ON;")

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

    connection: Connection = connect_or_create_database(vault_name, db_path)
    
    cur: Cursor = connection.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    cur.execute(f"""
    SELECT t.name, t.description, ts.tag FROM '{vault_name}' AS t
    LEFT JOIN {vault_name}_tags AS ts ON t.id = ts.element_id
    WHERE ts.tag = ?;
    """, (snippet_or_tag, )
    )
    results = cur.fetchall()

    connection.close()

    return results

def see_vault(vault_name: str|None, db_path: Path|None = None, list_db_tables: bool = False):
    """
    Prints all avaiable vaults in a specific database.
    """

    if vault_name is None and list_db_tables == False:
        raise NoOptions("Didn't receive neither a vault-name nor is list-db-tables enabled.")

    if vault_name:
        if not database_exists(vault_name, db_path):
            raise DbNotExistent("Database or table doesn't exist.")
        connection = connect_or_create_database(vault_name, db_path)
    else:
        db_path = get_full_db_path(db_path)
        connection = sqlite3.connect(db_path)

    cur = connection.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    if not list_db_tables:
        cur.execute(f"SELECT vn.name, vn.description, vn.timedate, st.tag FROM {vault_name} AS vn LEFT JOIN {vault_name}_tags AS st ON vn.id == st.element_id;")
    else:
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table';")
    
    result = cur.fetchall()
    connection.close()

    return result

def remove_vault(
        vault_name: str,
        db_path: Path|None = None,
        just_entries: bool = False
):
    """
    Deletes a vault or/and its contents forever.
    """
    if vault_name is None:
        raise NoOptions("Vault Name not given.")

    if not database_exists(vault_name, db_path):
        raise DbNotExistent("Database or vault doesn't exists.")

    connection = connect_or_create_database(vault_name, db_path)
    cur = connection.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    if not check_table_security(vault_name):
        raise TableNameErr(f"Table called {vault_name} is not secure, and probably doesn't even exists, but somehow you got here.")

    if not just_entries:
        cur.execute(
            f"DROP TABLE IF EXISTS {vault_name};"
        )
        cur.execute(
            f"DROP TABLE IF EXISTS {vault_name}_tags;"
        )
    else:
        cur.execute(
            f"DELETE FROM {vault_name};"
        )
        cur.execute(
            f"DELETE FROM {vault_name}_tags;"
        )

    connection.commit()
    connection.close()

def delete_snippet(vault_name: str, snippet_or_tag_name: str, is_tag: bool = False, db_path: Path|None = None):
    """
    Removes the snippet from the vault.
    """
    if vault_name is None or snippet_or_tag_name is None:
        raise NoOptions("Vault Name or Snippet/Tag not given.")

    if not database_exists(vault_name, db_path):
        raise DbNotExistent("Database or vault doesn't exists.")

    if not check_table_security(vault_name):
        raise TableNameErr(f"Table called {vault_name} is not secure, and probably doesn't even exists, but somehow you got here.")

    connection = connect_or_create_database(vault_name, db_path)
    cur = connection.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")

    if not is_tag:
        cur.execute(
            f"""
            DELETE FROM {vault_name} WHERE name == ?;
            """, (snippet_or_tag_name, )
        )
    else:
        cur.execute(
            f"""
            DELETE FROM {vault_name} WHERE id IN (
                SELECT element_id FROM {vault_name}_tags WHERE tag = ?
            )
            """, (snippet_or_tag_name,)
        )

    connection.commit()
    connection.close()