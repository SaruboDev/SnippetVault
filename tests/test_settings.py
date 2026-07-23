from snippetvault.functions import settings

from unittest.mock import MagicMock, patch
import pytest as pt
import pathlib as pl

@pt.fixture(scope="function")
def fake_settings_path(tmp_path):
    fake_dir: pl.Path = tmp_path / "test_dir"
    fake_dir.mkdir()
    return fake_dir


def test_check_and_create_settings(fake_settings_path) -> None:
    """
    Tests the check and create settings functions.
    Asserts if the response from the function is 'True', meaning it worked, and also asserts if the settings file
    actually exists.
    """

    response: bool = settings.check_settings_file(
        file_path = fake_settings_path,
        db_path = fake_settings_path
    )

    assert response == True
    fake_dir_settings = fake_settings_path / "settings.toml"
    assert fake_dir_settings.exists()


def test_read_settings(fake_settings_path) -> None:
    """
    Tests the "read settings" function, should return the same path as 'fake_settings_path'.
    """

    response = settings.read_settings_file(
        key_name = "database_path",
        file_path = fake_settings_path,
        db_path = fake_settings_path
    )

    assert response == fake_settings_path
    # NOTE: Maybe also assert for the whole file, not just a key. But how would i compare a full file? by reading it again? Dumb


def test_change_settings(fake_settings_path):
    """
    Tests the 'change settings' function, literally uses the other functions as well.
    """
    new_fake_db_path = fake_settings_path / "database/"

    response = settings.change_settings(new_fake_db_path, "database_path", fake_settings_path, fake_settings_path)
    
    assert response == True

    response = settings.read_settings_file(key_name = "database_path", file_path = fake_settings_path, db_path = new_fake_db_path)
    
    assert response == new_fake_db_path