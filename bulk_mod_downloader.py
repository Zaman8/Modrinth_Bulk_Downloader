#!/usr/bin/env python3
"""
Modrinth Mod Downloader
Reads mod IDs from a config file, MC version from CLI args.
"""

import json
import sys
import hashlib
import argparse
import requests
import configparser
from pathlib import Path
from tqdm import tqdm

api_base = "https://api.modrinth.com/v2"
headers = {"User-Agent": "my-server-mod-updater/1.0 zastiffler@gmail.com"}

def load_config(config_path="config.ini"):
    """Load global config from an ini file."""
    path = Path(config_path)
    if not path.exists():
        print(f"Error: Global config file not found: {config_path}")
        sys.exit(1)

    cfg = configparser.ConfigParser()
    cfg.read(path)
    return cfg

def parse_args(cfg):
    defaults = cfg["defaults"]
    parser = argparse.ArgumentParser(
        description="Download latest Modrinth mod jars for a given MC version."
    )
    parser.add_argument(
        "mc_version",
        nargs="?",
        default=None,
        help="Minecraft version to target (e.g. 1.21.1), Omit to use latest full release"
    )
    parser.add_argument(
        "--loader", "-l",
        default=defaults["loader"],
        choices=["fabric", "forge", "neoforge", "quilt"],
        help=f"Mod loader (default: {defaults['loader']})"
    )
    parser.add_argument(
        "--mods", "-m",
        default=defaults["mod_list"],
        help=f"Path to mod list file (default: {defaults['mod_list']})"
    )
    parser.add_argument(
        "--output", "-o",
        default=defaults["output_dir"],
        help=f"Output directory for jars (default: {defaults['output_dir']})"
    )
    parser.add_argument(
        "--global-config", "-g",
        default="config.ini",
        help="Path to global config file (default: config.ini)"
    )
    return parser.parse_args()

def get_latest_mc_release(headers):
    """Fetch the latest stable Minecraft release version from Mojang's manifest."""
    url = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()["latest"]["release"]

def get_projects_info(mod_ids, api_base, headers):
    """Fetch metadata for multiple projects in a single API call."""
    url = f"{api_base}/projects"
    params = {"ids": json.dumps(mod_ids)}
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()

    # Return a dict keyed by both id and slug for easy lookup
    result = {}
    for project in resp.json():
        result[project["id"]] = project
        result[project["slug"]] = project
    return result

def load_mod_list(config_path):
    """
    Load mod slugs/IDs from a plaintext file.
    - One mod per line
    - Lines starting with # are treated as comments
    - Blank lines are ignored
    """
    path = Path(config_path)
    if not path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    mods_list = []
    with open(path, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                mods_list.append(stripped.split()[0]) #only take first white-space delimited token (allows for inline comments)

    if not mods_list:
        print(f"Error: No mods found in {config_path}")
        sys.exit(1)

    return mods_list

def get_latest_version(project_slug, mc_version, loader, api_base, headers):
    """Fetch the latest compatible version for a mod."""
    url = f"{api_base}/project/{project_slug}/version"
    params = {
        "game_versions": json.dumps([mc_version]),
        "loaders": json.dumps([loader]),
    }
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    versions = resp.json()
    return versions[0] if versions else None

def sha512_of_file(path):
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def download_mod(version_data, output_dir):
    """Download the primary jar file for a version."""
    files = version_data["files"]
    primary = next((f for f in files if f.get("primary")), files[0])

    # Determine URL and expected hash for Mod file
    filename = primary["filename"]
    url = primary["url"]
    expected_hash = primary["hashes"]["sha512"]
    dest = Path(output_dir) / filename

    # If file already exists in destination and hash matches then skip download & return false
    if dest.exists() and sha512_of_file(dest) == expected_hash:
        print(f"  ✓ Already up-to-date: {filename}")
        return False

    # If either file doesn't exist or hash doesn't match then download updated mod file
    print(f"  ↓ Downloading: {filename}")
    resp = requests.get(url, headers=headers, stream=True)
    resp.raise_for_status()
    
    # Determine total download size for pretty download bar (tqdm)
    download_size = int(resp.headers.get("content-length"), 0)

    with open(dest, "wb") as f, tqdm(
        desc=f"  ↓ {filename}",
        total=download_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        leave=True,
    ) as bar:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))

    actual_hash = sha512_of_file(dest)
    if actual_hash != expected_hash:
        dest.unlink()
        raise ValueError(f"Hash mismatch for {filename}! File deleted.")

    return True

def main():
    # Parse arg logic with defaults passed through from init
    global_config_path = next(
        (sys.argv[i+1] for i, a in enumerate(sys.argv) if a in ("--global-config", "-g")),
        "config.ini"
    )
    cfg = load_config(global_config_path)
    args = parse_args(cfg)

    api_base = cfg["api"]["base_url"]
    headers = {"User-Agent": cfg["api"]["user_agent"]}

    # If no MC version is specified pull the latest stable release
    if args.mc_version is None:
        print("No version specified, fetching latest stable release...")
        args.mc_version = get_latest_mc_release(headers)

    # Load mods from user-defined list and prep output directory
    mods_list = load_mod_list(args.mods)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Output key info prior to downloading mods
    print(f"Minecraft {args.mc_version} | Loader: {args.loader} | Mods: {len(mods_list)}")
    print(f"Output Folder: {output_dir.resolve()}\n")

    # Single batch lookup for all project metadata
    print("Fetching project info...")
    projects_info = get_projects_info(mods_list, api_base, headers)

    # Download each mod loaded from file
    updated = 0
    for mod_id in mods_list:

        # Print human-readable mod name
        mod_info = projects_info[mod_id]
        display_name = f"{mod_info.get('title', mod_id)} ({mod_info.get('slug', '?')})"
        print(f"[{display_name}]", end="")
        
        # Download mods and report status
        try:
            version = get_latest_version(mod_id, args.mc_version, args.loader, api_base, headers)
            if not version:
                print(f"  ✗ No compatible version found for {args.mc_version} / {args.loader}")
                continue
            if download_mod(version, output_dir):
                updated += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")

    # Confirm execution
    print(f"\nDone. {updated} mod(s) updated → {output_dir.resolve()}")

if __name__ == "__main__":
    main()