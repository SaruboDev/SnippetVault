import typer
from typing import Annotated, Optional
from pathlib import Path
import sqlite3

from .functions import sql_functions as sql_fn
from .functions import settings

from sqlite3 import Connection, Cursor

# from rich import print
from rich.syntax import Syntax
from rich.console import Console
from rich.table import Table
import tomlkit

app = typer.Typer()
err_console = Console(stderr=True)
out_console = Console(stderr=False)

@app.command()
def create_vault(name: Annotated[str, typer.Argument()] = "standard_vault") -> None:
    """
    Creates a new vault to store whatever you want.
    """
    try:
        # if sql_fn.check_or_create_database(name) == True:
        #     out_console.print(f"Database called {name} already exists. Closing.")
        #     raise typer.Exit(code = 0)

        if sql_fn.check_or_create_database(name) == False:
            out_console.print(
                f"Database [bold #687396]{name} [/bold #687396] doesn't exist."
            )

            reply: bool = typer.confirm("Want to create a new one?")
            if reply:
                connection = sql_fn.create_database(name)
                connection.close()
                out_console.print("Done!")
                raise typer.Exit(code = 0)
        
        out_console.print("Closing.")
        raise typer.Exit(code = 0)

    except sql_fn.TableNameErr as e:
        err_console.print(str(e))
        raise typer.Exit(code = 1)

@app.command()
def add_snippet(
        vault_name: str,
        snippet_name: str,
        description: str,
        tags: list[str]
    ) -> None:
    """
    Adds a new snippet to the specified vault.
    Example `add-snippet vault ls 'Lists all the files and directories in the current path or in a specified path.' cmd command-line`
    """
    try:
        sql_fn.add_to_vault(vault_name, snippet_name, description, tags)

    except (sql_fn.TableNameErr, sql_fn.DbNotExistent) as e:
        err_console.print(str(e))
        raise typer.Exit(code = 1)

@app.command()
def search(
    vault_name: str,
    snippet_or_tag: str,
    is_tag: bool = False
):
    """
    Searches in the given table for the snippet or tag.
    """
    try:
        results = sql_fn.search_in_vault(vault_name, snippet_or_tag, is_tag)
        table = Table()
        table.add_column("Snippet Name")
        table.add_column("Description")
        table.add_column("Tags")

        for result in results:
            table.add_row(result[0], result[1], result[2])

        out_console.print(table)

        raise typer.Exit(code = 0)

    except (sql_fn.TableNameErr, sql_fn.DbNotExistent) as e:
        err_console.print(str(e))
        raise typer.Exit(code = 1)

@app.command()
def see_vault(
    vault_name: Optional[str] = typer.Argument(None, help="Name of the vault (optional)"),
    list_db_tables: bool = False
):
    """
    Let's you see every note in the specified vault.
    If you don't specify a vault but insert '--list-db-tables' it will list all avaiable vaults in the database.
    """
    try:
        results = sql_fn.see_vault(vault_name, None, list_db_tables)

        if not list_db_tables:
            table = Table()
            table.add_column("Snippet Name")
            table.add_column("Description")
            table.add_column("Timedate")
            table.add_column("Tags")

            for result in results:
                table.add_row(
                    result[0],
                    result[1],
                    result[2],
                    result[3]
                )
            
            out_console.print(table)
        else:
            table = Table()
            table.add_column("Tables")
            for result in results:
                result = result[0]
                if result == "sqlite_sequence":
                    continue
                table.add_row(result)

            out_console.print(table)
        raise typer.Exit(code = 0)

    except (sql_fn.TableNameErr, sql_fn.DbNotExistent, sql_fn.NoOptions) as e:
        err_console.print(str(e))
        raise typer.Exit(code = 1)

@app.command()
def change_settings(settings_name: str, new_value) -> None:
    """
    Changes any specified settings.
    """
    try:
        settings.change_settings(new_value, settings_name)
    except (settings.OSCheckErr, settings.KeyNameErr, settings.SettingsNoExists, settings.GeneralSettingsErr) as e:
        err_console.print(e)
        raise typer.Exit(code = 1)

@app.command()
def see_settings(key_name: Annotated[str, typer.Argument()] = None) -> None:
    """
    Prints the user's settings.
    """

    try:
        settings_print = settings.read_settings_file(key_name)
        if settings_print is False:
            err_console.print("No settings to show! Congrats, i don't know how you managed to get this.")
            raise typer.Exit(code = 1)
        syntx = Syntax(settings_print, "toml", line_numbers = False)
        out_console.print(syntx)

    except (settings.OSCheckErr, settings.GeneralSettingsErr) as e:
        err_console.print(e)
        raise typer.Exit(code = 1)

if __name__ == "__main__":
    app()
