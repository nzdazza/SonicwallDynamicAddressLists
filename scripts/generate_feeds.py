#!/usr/bin/env python3
"""Build validated, SonicWall-compatible DEAG files from configured sources."""

from __future__ import annotations

import ipaddress
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "feeds.json"
MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024


def download(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("feed sources must use HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": "SonicwallDynamicAddressLists/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status} from {url}")
        payload = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(payload) > MAX_DOWNLOAD_BYTES:
        raise ValueError(f"feed exceeds {MAX_DOWNLOAD_BYTES} bytes")
    return payload


def source_entries(payload: bytes, source_format: str) -> list[str]:
    if source_format == "json_array":
        values = json.loads(payload)
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError("JSON source must be an array of strings")
        return values
    if source_format == "plaintext":
        return [line.strip() for line in payload.decode("utf-8-sig").splitlines()
                if line.strip() and not line.lstrip().startswith("#")]
    raise ValueError(f"unsupported source_format: {source_format}")


def validated_networks(values: list[str], family: str):
    version = {"ipv4": 4, "ipv6": 6}.get(family)
    if version is None:
        raise ValueError(f"unsupported address_family: {family}")
    networks = set()
    for value in values:
        text = value.strip()
        network = ipaddress.ip_network(text, strict=True) if "/" in text else ipaddress.ip_network(text)
        if network.version != version:
            raise ValueError(f"unexpected address family: {text}")
        networks.add(network)
    return networks


def render(feed: dict, payload: bytes) -> tuple[str, int, int]:
    values = source_entries(payload, feed["source_format"])
    minimum, maximum = int(feed["minimum_entries"]), int(feed["maximum_entries"])
    if not minimum <= len(values) <= maximum:
        raise ValueError(f"source entry count {len(values)} is outside configured range {minimum}..{maximum}")
    networks = validated_networks(values, feed["address_family"])
    if feed.get("collapse_cidrs", False):
        networks = set(ipaddress.collapse_addresses(networks))
    ordered = sorted(networks, key=lambda item: (item.version, int(item.network_address), item.prefixlen))
    lines = [str(item.network_address) if item.prefixlen == item.max_prefixlen else str(item)
             for item in ordered]
    return "\n".join(lines) + "\n", len(values), len(lines)


def output_path(relative: str) -> Path:
    candidate = (ROOT / relative).resolve()
    feeds_root = (ROOT / "feeds").resolve()
    if candidate.parent != feeds_root or candidate.suffix != ".txt":
        raise ValueError("output must be a .txt file directly inside feeds/")
    return candidate


def main() -> int:
    feeds = json.loads(MANIFEST.read_text(encoding="utf-8")).get("feeds")
    if not isinstance(feeds, list) or not feeds:
        raise ValueError("config/feeds.json must contain a non-empty feeds array")
    generated = []
    for feed in feeds:
        body, source_count, output_count = render(feed, download(feed["source"]))
        generated.append((output_path(feed["output"]), body))
        print(f"{feed['name']}: {source_count} source entries -> {output_count} output entries")
    for path, body in generated:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(body, encoding="ascii", newline="\n")
        temporary.replace(path)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
