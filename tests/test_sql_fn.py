from snippetvault.functions import sql_functions as sql_fn

from unittest.mock import MagicMock, patch
import pytest as pt
import pathlib as pl

from sqlite3 import Connection

@pt.fixture(scope="function")
def fake_db_path(tmp_path):
    fake_dir: pl.Path = tmp_path / "test_dir"
    fake_dir.mkdir()
    return fake_dir

def test_check_and_create_db(fake_db_path):
    response = sql_fn.check_or_create_database("test", fake_db_path)
    if response is False:
        reply = sql_fn.create_database("test", fake_db_path)

    assert isinstance(reply, Connection)

    assert pl.Path(fake_db_path / "database.db").exists()
    reply.close()

def test_add_snippet(fake_db_path):
    sql_fn.add_to_vault(
        "test", "snippet test", "description test", "python", fake_db_path
    )

    connection = sql_fn.create_database("test", fake_db_path)
    cur = connection.cursor()
    cur.execute("SELECT * FROM test")
    rows = cur.fetchall()
    connection.close()