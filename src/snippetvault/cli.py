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

def _ask_reply(results) -> int:
    reply: str = typer.prompt("Which index would you like to edit? [0 is the first]: ", default = "0")
    if not reply.isdigit() or (int(reply) <= 0 and int(reply) >= len(results)):
        out_console.print("Selected index is either not digit or in range.")
        raise typer.Exit(code = 0)
    
    return int(reply)

@app.command()
def create_vault(vault_name: Annotated[str, typer.Argument()] = "standard_vault") -> None:
    """
    Creates a new vault to store whatever you want.
    """
    try:
        if sql_fn.database_exists(vault_name) == False:
            out_console.print(
                f"Database [bold #687396]{vault_name} [/bold #687396] doesn't exist."
            )

            reply: bool = typer.confirm("Want to create a new one?")
            if reply:
                connection = sql_fn.connect_or_create_database(vault_name)
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

    except (sql_fn.TableNameErr, sql_fn.DbNotExistent, sql_fn.SameItem) as e:
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
                    ",".join(result[3])
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
def remove_vault(
    vault_name: str,
    just_entries: bool = False
):
    """
    Deletes a vault or/and its contents forever.
    """
    try:
        if not just_entries:
            reply: bool = typer.confirm(
                f"Database {vault_name} and {vault_name}_tags will be [bold #d42619]removed along with its contents[/bold #d42619] forever, continue?"
            )
        else:
            reply: bool = typer.confirm(
                f"All contents inside {vault_name} and {vault_name}_tags will be [bold #d42619]removed[/bold #d42619] forever, continue?"
            )
        if reply:
            sql_fn.remove_vault(vault_name, None, just_entries)
            out_console.print("Done.")
        else:
            out_console.print("Canceled.")
        
        raise typer.Exit(code = 0)

    except (sql_fn.TableNameErr, sql_fn.DbNotExistent) as e:
        err_console.print(str(e))
        raise typer.Exit(code = 1)

@app.command()
def import_database(
    database_path: str
):
    """
    Imports and replaces the existing database (if any) with the specified one.
    """
    try:
        sql_fn.import_database(database_path)
        out_console.print("Import successful.")

    except (FileNotFoundError, sqlite3.Error) as e:
        err_console.print(str(e))
        raise typer.Exit(code = 1)

@app.command()
def export_database(
    export_path: str|None = None
):
    """
    Exports a database in the given directory.
    If not given any path, it will dump the file into the home directory under the 'dump_snippetvault.db' filename.
    """
    try:
        sql_fn.export_database(export_path)
        out_console.print("Export successful.")

    except (Exception, sqlite3.Error) as e:
        err_console.print(str(e))
        raise typer.Exit(code = 1)

@app.command()
def delete_snippet(
    vault_name: str,
    snippet_or_tag_name: str,
    is_tag: bool = False
):
    """
    Removes the snippet from the vault.
    """
    try:
        results = sql_fn.search_in_vault(vault_name, snippet_or_tag_name, is_tag)
        table = Table()
        table.add_column("Index")
        table.add_column("Snippet Name")
        table.add_column("Description")
        table.add_column("Tags")

        idx: int = 0
        for result in results:
            table.add_row(str(idx), result[0], result[1], result[2])
            idx += 1

        out_console.print(table)
        if not results:
            out_console.print(f"No result for {snippet_or_tag_name}.")
            raise typer.Exit(code = 0)

        to_delete: list = results[_ask_reply(results)]
        sql_fn.delete_snippet(vault_name, to_delete, is_tag)
        out_console.print("Done.")
        raise typer.Exit(code = 0)

    except (sql_fn.TableNameErr, sql_fn.DbNotExistent, sql_fn.NoOptions) as e:
        err_console.print(str(e))
        raise typer.Exit(code = 1)

@app.command()
def edit_snippet(
    vault_name: str,
    snippet_or_tag: str,
    is_tag: bool = False
):
    """
    Edits the snippet.
    """
    try:
        results = sql_fn.search_in_vault(vault_name, snippet_or_tag, is_tag)
        table = Table()
        table.add_column("Index")
        table.add_column("Snippet Name")
        table.add_column("Description")
        table.add_column("Tags")

        idx: int = 0
        for result in results:
            table.add_row(str(idx), result[0], result[1], result[2])
            idx += 1

        out_console.print(table)
        if not results:
            out_console.print(f"No result for {snippet_or_tag}.")
            raise typer.Exit(code = 0)

        to_edit: list = results[_ask_reply(results)]
        new_name: str = typer.prompt("New name for snippet (can leave empty for no changes): ", type = str, default = "")
        new_desc: str = typer.prompt("New description for the snippet (can leave empty for no changes): ", type = str, default = "")
        tags_to_delete: str = typer.prompt("Which tags do you want to delete (leave empty for no deletion, or separate with commas multiple tags): ", type = str, default = "")
        tags_to_add: str = typer.prompt("Which tags do you want to add (leave empty for no addition, or separate with commas for multiple tags): ", type = str, default = "")

        sql_fn.edit_snippet(
            vault_name, to_edit, new_name, new_desc, tags_to_delete, tags_to_add
        )
        out_console.print("Snippet edited successfully.")

    except (sqlite3.Error, sql_fn.EditError, Exception) as e:
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
