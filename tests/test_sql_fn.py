from snippetvault.functions import sql_functions as sql_fn

from unittest.mock import MagicMock, patch, ANY
import pytest as pt
import pathlib as pl

from sqlite3 import Connection
import json

@pt.fixture(scope="function")
def fake_db_path(tmp_path):
    fake_dir: pl.Path = tmp_path / "test_dir"
    fake_dir.mkdir()
    return fake_dir

@pt.fixture()
def new_db(fake_db_path):
    sql_fn.connect_or_create_database("test", fake_db_path / "database.db")

@pt.fixture(scope="function")
def old_db(fake_db_path, new_db):
    sql_fn.add_to_vault(
        "test", "snippet test", "description test", ["python", "coding"], fake_db_path
    )
    sql_fn.connect_or_create_database("test2", fake_db_path / "database.db")
    sql_fn.add_to_vault(
        "test2", "snippet test2", "description test2", ["sh"], fake_db_path
    )
    sql_fn.add_to_vault(
            "test2", "snippet test3", "description test3", ["aaah"], fake_db_path
        )
    sql_fn.export_database(
        fake_db_path,
        fake_db_path / "database.db"
    )
    sql_fn.delete_snippet(
        "test2", "snippet test3", False, fake_db_path
    )

    return pl.Path(fake_db_path) / "dump_snippetvault.db"

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
        ["test_tag", "secondary_tag"],
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
    for item in no_tag_res:
        noname, nodesc, notags = item
        assert noname == "snippet test"
        assert nodesc == "description test"
        assert notags == "secondary_tag,test_tag"

    assert yes_tag_res == [("snippet test", "description test", "test_tag"), ("snippet test 2", "description test", "test_tag")]

@pt.mark.parametrize(
        "vault_name, list_db_tables, expected",
        [
            ("test", False, [["snippet test", "description test", ANY, ["test_tag"]]]),
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

@pt.mark.parametrize(
        "is_tag, snippet_or_tag_name, expected",
        [
            (False, ["snippet test", "description test", ""], []),
            (True, ["snippet test", "description test", "test_tag"], [])
        ]
)
def test_delete_snippet(
        fake_db_path,
        new_db,
        is_tag: bool,
        snippet_or_tag_name: str,
        expected
):
    sql_fn.add_to_vault(
        "test",
        "snippet test",
        "description test",
        ["test_tag"],
        fake_db_path
    )

    sql_fn.delete_snippet(
        "test",
        snippet_or_tag_name,
        is_tag,
        fake_db_path
    )

    results = sql_fn.see_vault(
        "test",
        fake_db_path,
        False
    )
    connection = sql_fn.connect_or_create_database("test", fake_db_path)
    cur = connection.cursor()
    cur.execute("SELECT * FROM test_tags;")
    results_tags = cur.fetchall()
    connection.close()

    assert results == expected
    assert results_tags == expected


def test_export_db(
        fake_db_path,
        new_db
):
    sql_fn.add_to_vault(
        "test", "snippet test", "description test", ["python"], fake_db_path
    )
    sql_fn.export_database(
        fake_db_path,
        fake_db_path / "database.db"
    )

    full_path = pl.Path(fake_db_path) / "dump_snippetvault.db"
    assert full_path.exists()

def test_import_db(
        fake_db_path,
        old_db
):
    ## Only removing one so we check both cases.
    sql_fn.remove_vault(
        "test",
        fake_db_path
    )
    sql_fn.import_database(
        old_db,
        fake_db_path
    )

    res = sql_fn.see_vault(
        "test",
        fake_db_path
    )
    res = [(name, desc, tags) for name, desc, time, tags in res]

    assert res == [("snippet test", "description test", ["coding", "python"])]

    res = sql_fn.see_vault(
        "test2",
        fake_db_path
    )
    res = [(name, desc, tags) for name, desc, time, tags in res]
    
    assert res == [('snippet test2', 'description test2', ['sh']), ('snippet test3', 'description test3', ['aaah'])]


@pt.mark.parametrize(
        "to_edit, new_name, new_desc, tags_to_delete, tags_to_add",
        [
            (
                ["testname", "description test", "python,super,mega"],
                "newname", "new desc", "", ""
            ),
            (
                ["testname", "description test", "python,super,mega"],
                "", "", "python, super", "coding, language"
            )
        ]
)
def test_edit_snipped(
    fake_db_path,
    new_db,
    to_edit,
    new_name,
    new_desc,
    tags_to_delete,
    tags_to_add
):
    sql_fn.add_to_vault(
        "test", "testname", "description test", ["python", "super", "mega"], fake_db_path
    )
    sql_fn.edit_snippet(
        "test", to_edit, new_name, new_desc, tags_to_delete, tags_to_add, fake_db_path
    )

    if new_name: # This is for the name and description edit test.
        res = sql_fn.search_in_vault(
            "test",
            new_name,
            False,
            fake_db_path
        )
        assert res == [('newname', 'new desc', 'mega,python,super')]
    else: # This is for the tags edit test.
        res = sql_fn.search_in_vault(
            "test",
            "testname",
            False,
            fake_db_path
        )
        assert res == [('testname', 'description test', 'coding,language,mega')]

def test_no_tags(
        fake_db_path,
        new_db
):
    sql_fn.add_to_vault(
        "test", "testname", "description test", ["python", "super", "mega"], fake_db_path
    )

    try:
        sql_fn.edit_snippet(
            "test", ["testname", "description test", "python,super,mega"], "", "", "python, super, mega", "", fake_db_path
        )
        assert False
    except sql_fn.EditError:
        assert True

def test_dupe(
        fake_db_path,
        new_db
):
    sql_fn.add_to_vault(
        "test", "testname", "description test", ["python", "super", "mega"], fake_db_path
    )
    try:
        sql_fn.add_to_vault(
            "test", "testname", "description test", ["python", "super", "mega"], fake_db_path
        )
        assert False
    except sql_fn.SameItem:
        assert True
