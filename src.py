#!/usr/bin/env python3
"""
Modrinth Mod Downloader
Reads mod IDs from a config file, MC version from CLI args.
"""

import json
import os
import sys
import hashlib
import argparse
import requests
from pathlib import Path

API_BASE = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "my-server-mod-updater/1.0 (your@email.com)"}

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

    mods = []
    with open(path, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                mods.append(stripped)

    if not mods:
        print(f"Error: No mods found in {config_path}")
        sys.exit(1)

    return mods

def parse_args():
    parser = argparse.ArgumentParser(
        description="Download latest Modrinth mod jars for a given MC version."
    )
    parser.add_argument(
        "mc_version",
        help="Minecraft version to target (e.g. 1.21.1)"
    )
    parser.add_argument(
        "--loader", "-l",
        default="fabric",
        choices=["fabric", "forge", "neoforge", "quilt"],
        help="Mod loader (default: fabric)"
    )
    parser.add_argument(
        "--config", "-c",
        default="mods.txt",
        help="Path to mod list config file (default: mods.txt)"
    )
    parser.add_argument(
        "--output", "-o",
        default="./mods",
        help="Output directory for downloaded jars (default: ./mods)"
    )
    return parser.parse_args()

def get_latest_version(project_slug, mc_version, loader):
    """Fetch the latest compatible version for a mod."""
    url = f"{API_BASE}/project/{project_slug}/version"
    params = {
        "game_versions": json.dumps([mc_version]),
        "loaders": json.dumps([loader]),
    }
    resp = requests.get(url, params=params, headers=HEADERS)
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

    filename = primary["filename"]
    url = primary["url"]
    expected_hash = primary["hashes"]["sha512"]
    dest = Path(output_dir) / filename

    if dest.exists() and sha512_of_file(dest) == expected_hash:
        print(f"  ✓ Already up-to-date: {filename}")
        return False

    print(f"  ↓ Downloading: {filename}")
    resp = requests.get(url, headers=HEADERS, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    actual_hash = sha512_of_file(dest)
    if actual_hash != expected_hash:
        dest.unlink()
        raise ValueError(f"Hash mismatch for {filename}! File deleted.")

    return True

def main():
    args = parse_args()

    mods = load_mod_list(args.config)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Minecraft {args.mc_version} | Loader: {args.loader} | Mods: {len(mods)}")
    print(f"Output: {output_dir.resolve()}\n")

    updated = 0
    for slug in mods:
        print(f"[{slug}]")
        try:
            version = get_latest_version(slug, args.mc_version, args.loader)
            if not version:
                print(f"  ✗ No compatible version found for {args.mc_version} / {args.loader}")
                continue
            if download_mod(version, output_dir):
                updated += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\nDone. {updated} mod(s) updated → {output_dir.resolve()}")

if __name__ == "__main__":
    main()