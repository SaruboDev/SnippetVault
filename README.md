<h1 align="center">SnippetVault</h1>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff" alt="Python">
  &emsp;
  <img src="https://img.shields.io/badge/uv-261230.svg?logo=uv&logoColor=#de5fe9" alt="UV">
  &emsp;
  <img src="https://img.shields.io/badge/SQLite-%2307405e.svg?logo=sqlite&logoColor=white" alt="sql">
</p>


A lightweight CLI tool that allows you able to create vaults and add snippets in them as NAME - DESCRIPTION - TAGS, and show all made snippets!
Made in python with SQLite. 

## Features
- Create "vaults" in a SQLite Database. You can change the settings to decide where you want to store the database.
- Add snippets with `NAME - DESCRIPTION - TAGS` in the specified vault, you can have as many vaults as you want.
- Prevents SQL Injections on your vault's name by using regex.
- Tags managed by a separate table with Foreign Keys.
- CLI Interface made with the `typer` and `rich` libraries!
- Automated CI pipeline with Github Actions on every main branch push!
- `Pytest` used to guarantee working status.
- `UV` used for blazing-fast package manager!

## I want to try!
You can use the release build by:
### Install directly from github.
1. Open your terminal and use:
- If you use pip: `pip install https://github.com/SaruboDev/SnippetVault/releases/download/v1.0.0/snippetvault-1.0.0-py3-none-any.whl` (or any other link to the version you'd like, 1.0.0 is a placeholder for whatever version will be in the future!)
- If you use uv: `uv pip install same_link_here` or `uv tool install same_link_here`
2. Done!
### Download the files locally.
1. Download the release you wish to use (the .whl file is enough, but if you have any error you can use the .tar.gz one).
2. Open your terminal and use:
- If you use pip: `pip install path_to_the_download_file`
- If you use uv: `uv pip install path_to_the_download_file` or `uv tool install path_to_the_download_file`
3. Done!
### Try the main WIP repo with:
1. Clone the repository: `git clone https://github.com/SaruboDev/SnippetVault`
2. With your terminal, go in the root folder of the project.
3. Sync the dependencies: `uv sync`
4. Use `uv run snippetvault --help` to see all possible commands!

### Start guide!
Create your vault!
```bash
uv run snippetvault create-vault custom-vault-name
```
Add your snippet!
```bash
uv run snippetvault add-snippet custom-vault-name "snippet name" "I'm the snippet description!" tag1 tag2 tagN
```
Show all snippets (with option to add `--list-db-tables` to show all avaiable vaults)
```bash
uv run snippetvault see-vault custom-vault-name
```
## Future Updates
If you want to suggest more features or tell me about bugs/other, feel free to open pull requests or issues!
- [X] Turn it into a downloadable package for pip or as an installer.
- [X] Add name and tags search.
- [x] Add possibility to remove a snippet.
- [x] Add possibility to remove a vault.
- [X] Add possibility to edit a snippet and/or it's tags.
- [X] Add possibility to export or import a vault.
