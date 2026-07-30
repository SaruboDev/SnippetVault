from snippetvault.functions import sql_functions as sql_fn

from unittest.mock import MagicMock, patch, ANY
import pytest as pt
import pathlib as pl

from sqlite3 import Connection

@pt.fixture(scope="function")
def fake_db_path(tmp_path):
    fake_dir: pl.Path = tmp_path / "test_dir"
    fake_dir.mkdir()
    return fake_dir

@pt.fixture()
def new_db(fake_db_path):
    sql_fn.connect_or_create_database("test", fake_db_path / "database.db")

def test_check_and_create_db(fake_db_path):
    response = sql_fn.database_exists("test", fake_db_path)
    if response is False:
        reply = sql_fn.connect_or_create_database("test", fake_db_path)

    assert isinstance(reply, Connection)

    assert pl.Path(fake_db_path / "database.db").exists()
    reply.close()

def test_add_snippet(fake_db_path, new_db):
    sql_fn.add_to_vault(
        "test", "snippet test", "description test", ["python"], fake_db_path
    )

    ## Check if it actually added the snippet.
    connection = sql_fn.connect_or_create_database("test", fake_db_path)
    cur = connection.cursor()
    cur.execute("SELECT t.name, t.description, tt.tag FROM test AS t LEFT JOIN test_tags AS tt ON t.id = tt.element_id")
    rows = cur.fetchall()

    assert rows == [("snippet test", "description test", "python")]
    connection.close()

def test_search_in_vault(fake_db_path, new_db):
    sql_fn.add_to_vault(
        "test",
        "snippet test",
        "description test",
        ["test_tag"],
        fake_db_path
    )
    sql_fn.add_to_vault(
        "test",
        "snippet test 2",
        "description test",
        ["test_tag"],
        fake_db_path
    )

    no_tag_res = sql_fn.search_in_vault(
        "test",
        "snippet test",
        False,
        fake_db_path
    )
    yes_tag_res = sql_fn.search_in_vault(
        "test",
        "test_tag",
        True,
        fake_db_path
    )

    assert no_tag_res == [("snippet test", "description test", "test_tag")]
    assert yes_tag_res == [("snippet test", "description test", "test_tag"), ("snippet test 2", "description test", "test_tag")]

@pt.mark.parametrize(
        "vault_name, list_db_tables, expected",
        [
            ("test", False, [("snippet test", "description test", ANY, "test_tag")]),
            (None, True, [("test",), ("sqlite_sequence",), ("test_tags",)]),
            ("test", True, [("test",), ("sqlite_sequence",), ("test_tags",)])
        ]
)
def test_see_vaults(
    fake_db_path,
    new_db,
    vault_name: str|None,
    list_db_tables: bool,
    expected: list
):
    sql_fn.add_to_vault(
        "test",
        "snippet test",
        "description test",
        ["test_tag"],
        fake_db_path
    )

    results = sql_fn.see_vault(
        vault_name,
        fake_db_path,
        list_db_tables
    )

    assert results == expected

@pt.mark.parametrize(
        "just_entries, expected",
        [
            (True, True),
            (False, False)
        ]
)
def test_delete_table(
    fake_db_path,
    new_db,
    just_entries: bool,
    expected
):
    sql_fn.add_to_vault(
        "test",
        "snippet test",
        "description test",
        ["test_tag"],
        fake_db_path
    )
    sql_fn.remove_vault("test", fake_db_path, just_entries)

    result = sql_fn.database_exists("test", fake_db_path)

    assert result == expected