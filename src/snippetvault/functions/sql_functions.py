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

class SameItem(Exception):
    pass

class EditError(Exception):
    pass

def check_table_security(name: str) -> bool:
    """
    Quick regex filter.
    """

    if not re.match("^[a-zA-Z0-9_]+$", name):
        raise TableNameErr("Table name not valid or unsafe!")
    return True

def check_if_dupe(
        vault_name: str,
        snippet_name: str,
        description: str,
        db_path: Path|None = None
):
    """
    Checks if a snippet name and description already exists.
    """
    connection: Connection = connect_or_create_database(vault_name, db_path)
    check = search_in_vault(vault_name, snippet_name, False, db_path)
    if check:
        for item in check:
            if not item or (item[0] == snippet_name and item[1] == description):
                connection.close()
                raise SameItem("Cannot have duplicated snippets!")

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

    check_if_dupe(vault_name, snippet_name, description, db_path)

    cur.execute(f"INSERT INTO {vault_name} (name, description) VALUES(?, ?)", (snippet_name, description))
    last_id = cur.lastrowid

    for tag in tags:
        cur.execute(
            f"INSERT OR IGNORE INTO '{vault_name}_tags' (element_id, tag) VALUES (?, ?)", (last_id, tag)
        )

    connection.commit()
    connection.close()

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
        SELECT t.name, t.description, GROUP_CONCAT(ts.tag) FROM "{vault_name}" AS t
        LEFT JOIN "{vault_name}_tags" AS ts ON t.id = ts.element_id
        WHERE t.name = ?
        GROUP BY t.id;
        """, (snippet_or_tag, )
        )
        results = cur.fetchall()
        connection.close()

        if results and results[0][0] is None: return None
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

    all_snippets = []
    if not list_db_tables:
        cur.execute(f"""
        SELECT vn.name, vn.description, vn.timedate, GROUP_CONCAT(st.tag) FROM {vault_name} AS vn
        LEFT JOIN {vault_name}_tags AS st ON vn.id == st.element_id
        GROUP BY vn.id;
        """)
        result = cur.fetchall()
        for row in result:
            name, desc, timedate, tags = row
            tag_list = tags.split(",") if tags else []
            all_snippets.append([name, desc, timedate, tag_list])
    else:
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table';")
        all_snippets = cur.fetchall()

    connection.close()
    return all_snippets

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
            DELETE FROM {vault_name} WHERE name == ? AND description == ?;
            """, (snippet_or_tag_name[0], snippet_or_tag_name[1])
        )
    else:
        cur.execute(
            f"""
            DELETE FROM {vault_name} WHERE id IN (
                SELECT element_id FROM {vault_name}_tags WHERE tag = ? AND name == ? AND description == ?
            );
            """, (snippet_or_tag_name[2], snippet_or_tag_name[0], snippet_or_tag_name[1])
        )

    connection.commit()
    connection.close()

def edit_snippet(vault_name: str, to_edit: list, new_name: str = "", new_desc: str = "",  tags_to_delete: str = "", tags_to_add: str = "", db_path: Path|None = None):
    """
    Edits the snippet, only changes the non-empty values of 'new_name' or 'new_desc'.
    """
    connection = connect_or_create_database(vault_name, db_path)
    connection.execute("PRAGMA foreign_keys = ON;")

    ## Checks if it WOULD become a dupe.
    if new_name and new_desc:
        check_if_dupe(vault_name, new_name, new_desc, db_path)
    ## Grabs the last id of the to_edit snippet.
    last_id = connection.execute(f"SELECT id FROM {vault_name} WHERE name == ? and description == ?;", (to_edit[0], to_edit[1])).fetchone()[0]
    if not last_id: raise ValueError("No id found, cannot edit snippet.")

    if new_name:
        connection.execute(
            f"""
            UPDATE {vault_name}
            SET name = ?
            WHERE id == ?;
            """, (new_name, last_id)
        )
    if new_desc:
        connection.execute(
            f"""
            UPDATE {vault_name}
            SET description = ?
            WHERE id == ?;
            """, (new_desc, last_id)
        )

    if tags_to_delete:
        tags_to_delete = [tag.strip() for tag in tags_to_delete.split(",")]
        tag_count: int = connection.execute(f"SELECT COUNT(*) FROM {vault_name}_tags WHERE element_id == ?;", (last_id, )).fetchone()[0]
        to_add: int = 0
        if tags_to_add:
            to_add = len(tags_to_add)
        tags_left: int = tag_count - len(tags_to_delete) + to_add

        if tags_left > 0:
            for tag in tags_to_delete:
                connection.execute(
                    f"""
                    DELETE FROM {vault_name}_tags
                    WHERE element_id == ? AND tag == ?;
                    """, (last_id, tag)
                ) 
        else:
            raise EditError("Cannot proceed adding or deleting tags because no snippets can have 0 tags.")

    if tags_to_add:
        tags_to_add = [tag.strip() for tag in tags_to_add.split(",")]
        for tag in tags_to_add:
            connection.execute(
                f"INSERT OR IGNORE INTO '{vault_name}_tags' (element_id, tag) VALUES (?, ?)", (last_id, tag)
            )

    connection.commit()
    connection.close()

def import_database(database_path: str|Path, db_path: str|Path|None = None):
    """
    Imports into an existing database with the data from the specified one.
    """
    db_path = get_full_db_path(db_path)
    database_path = Path(database_path)
    if not database_path.is_file() or database_path.suffix != ".db": raise FileNotFoundError("'database_path' doesn't return the correct file.")

    connection = sqlite3.connect(db_path)
    conn_temp = sqlite3.connect(":memory:")

    connection.execute("PRAGMA foreign_keys = ON;")
    conn_temp.execute("PRAGMA foreign_keys = ON;")

    with open(database_path, "r") as f:
        sql = f.read()
        conn_temp.executescript(sql)

    all_tables_names_import = conn_temp.execute(
        """
        SELECT name FROM sqlite_master WHERE type='table';
        """
    ).fetchall()
    all_tables_names_local = connection.execute(
        """
        SELECT name FROM sqlite_master WHERE type='table';
        """
    ).fetchall()
    all_imported = [
        table[0] for table in all_tables_names_import if table[0] != "sqlite_sequence" and not str(table[0]).endswith("_tags")
    ]
    all_local = [
        table[0] for table in all_tables_names_local if table[0] != "sqlite_sequence" and not str(table[0]).endswith("_tags")
    ]

    def _new_table(table_name: str):
        """
        Imports totally new tables with all their data.
        """
        connect_or_create_database(
            table_name,
            db_path
        )
        all_names = conn_temp.execute(f"SELECT name FROM {table_name}").fetchall()
        all_desc = conn_temp.execute(f"SELECT description FROM {table_name}").fetchall()
        all_tags = conn_temp.execute(f"SELECT element_id, tag FROM {table_name}_tags").fetchall()

        tags = {i: [] for i, in all_names}

        for id, tag in all_tags:
            name = all_names[id-1][0]
            tags[name].append(tag)

        for name, desc in zip(all_names, all_desc):
            add_to_vault(
                table_name,
                name[0],
                desc[0],
                tags[name[0]],
                db_path
            )

    def _already_exists(table_name: str):
        """
        If the table already exists locally, we want to import only the ones that have different name and description.
        """
        imp_names = conn_temp.execute(f"SELECT name FROM {table_name}").fetchall()
        imp_descs = conn_temp.execute(f"SELECT description FROM {table_name}").fetchall()
        imp_tags = conn_temp.execute(f"SELECT element_id, tag FROM {table_name}_tags").fetchall()

        imp_names= [name[0] for name in imp_names]
        imp_descs = [desc[0] for desc in imp_descs]

        local_names = connection.execute(f"SELECT name FROM {table_name}").fetchall()
        local_descs = connection.execute(f"SELECT description FROM {table_name}").fetchall()

        local_names = [name[0] for name in local_names]
        local_descs = [desc[0] for desc in local_descs]

        for imp_name, imp_desc in zip(imp_names, imp_descs):
            if imp_name in local_names and imp_desc in local_descs: continue # Are the same.

            # If not the same we can add them.
            tags = {i: [] for i in imp_names}

            for id, tag in imp_tags:
                name = imp_names[id-1]
                tags[name].append(tag)

            add_to_vault(
                table_name,
                imp_name,
                imp_desc,
                tags[imp_name],
                db_path
            )
    
    for table in all_imported:
        check_table_security(table)
        if table in all_local: _already_exists(table)
        else: _new_table(table)

    connection.commit()
    connection.close()

def export_database(export_path: str|Path = Path.home(), db_path: Path|None = None):
    """
    Exports a database in the given directory.
    """
    if db_path == None:
        db_path = get_full_db_path(None)
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON;")
    export_path = Path(export_path)

    full_exp: Path
    if export_path.is_dir():
        full_exp = export_path / "dump_snippetvault.db"
    else:
        full_exp = export_path

    with open(full_exp, "w") as f:
        for line in connection.iterdump():
            f.write("%s\n" % line)
