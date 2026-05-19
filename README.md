# Modrinth Bulk Downloader

A simple Python CLI for bulk downloading Minecraft mod JARs from [Modrinth](https://modrinth.com). Point it at a plain-text list of mod slugs or IDs, tell it your MC version and loader, and it fetches the latest compatible JAR for each one — skipping anything already up to date.

Good for: Syncing mods across machines or keeping a local mod library current without clicking through the Modrinth site one mod at a time.

---

## Requirements

- **Python 3.7+**
- [`requests`](https://pypi.org/project/requests/)
- [`tqdm`](https://pypi.org/project/tqdm/)

Install dependencies with:

```bash
pip install requests tqdm
```

---

## Quickstart

```
python bulk_mod_downloader.py [mc_version] [--loader LOADER] [--mods FILE] [--output DIR] [--global-config FILE]
```

### Arguments

| Argument | Short | Default | Description |
|---|---|---|---|
| `mc_version` | — | Latest stable release | Minecraft version to target (e.g. `1.21.1`). Omit to auto-fetch the latest. |
| `--loader` | `-l` | `fabric` | Mod loader: `fabric`, `forge`, `neoforge`, or `quilt`. |
| `--mods` | `-m` | `mods.txt` | Path to your mod list file. |
| `--output` | `-o` | `./mods` | Directory where JAR files are saved. Created if it doesn't exist. |
| `--global-config` | `-g` | `config.ini` | Path to the global config file. |

### Examples

```bash
# Download mods for Fabric 1.21.1 using defaults
python bulk_mod_downloader.py 1.21.1

# Specify a loader and a custom mod list
python bulk_mod_downloader.py 1.20.4 --loader forge --mods my_forge_mods.txt

# Auto-detect the latest MC release, save to a custom folder
python bulk_mod_downloader.py --output ~/minecraft/mods
```

### mods.txt

`mods.txt` is a plain-text file listing the mods you want to download — one per line. Each entry should be a Modrinth **slug** or **project ID**. You can find a mod's slug in its Modrinth URL: `modrinth.com/mod/<slug>`.

- Lines beginning with `#` are treated as comments and ignored.
- Blank lines are ignored.
- Anything after the first whitespace on a line is ignored, so you can add inline comments.

```text
# Modrinth mod list

# Performance
sodium
lithium
iris

# Utilities
P7dR8mSH  # fabric-api by project ID
```

---

## Configuration

Global defaults live in `config.ini`, which is read on every run. You can change these to avoid repeating common flags on the command line. CLI arguments always take precedence over values in this file.

```ini
[api]
base_url   = https://api.modrinth.com/v2
user_agent = Zaman8/Modrinth_Bulk_Downloader/1.0

[defaults]
loader     = fabric
mod_list   = mods.txt
output_dir = ./mods
```

### `[api]`

| Key | Description |
|---|---|
| `base_url` | Modrinth API endpoint. You shouldn't need to change this. |
| `user_agent` | User-agent string sent with API requests. Update this if you fork the project. |

### `[defaults]`

| Key | Description |
|---|---|
| `loader` | Default mod loader used when `--loader` is not passed. |
| `mod_list` | Default path to the mod list file used when `--mods` is not passed. |
| `output_dir` | Default output directory used when `--output` is not passed. |

To use a different config file entirely, pass `--global-config path/to/other.ini`.

---

*This project uses AI generated code reviewed by humans*