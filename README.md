# SonicWall Dynamic Address Lists

Validated external address feeds formatted for SonicWall Dynamic External Address Groups (DEAGs).

## Published feeds

| Feed | SonicWall download URL |
|---|---|
| Microsoft 365 Copilot MCP static egress | `https://raw.githubusercontent.com/nzdazza/SonicwallDynamicAddressLists/main/feeds/microsoft-365-copilot-mcp.txt` |

Configure the SonicWall object with protocol **HTTPS**, **FQDN disabled**, and periodic download enabled.

## Repository layout

- `config/feeds.json` is the manifest to edit when adding another feed.
- `scripts/generate_feeds.py` downloads, validates, deduplicates and optionally collapses addresses.
- `feeds/*.txt` contains generated SonicWall files, with one IP address or CIDR per line.
- `.github/workflows/update-feeds.yml` updates files every 12 hours and can be run manually.

## Adding another feed

Add an object to the `feeds` array in `config/feeds.json`. Supported source formats are `json_array` and `plaintext`. Every feed must specify conservative minimum and maximum entry counts.

```json
{
  "name": "example-feed",
  "source": "https://example.com/addresses.txt",
  "source_format": "plaintext",
  "output": "feeds/example-feed.txt",
  "address_family": "ipv4",
  "collapse_cidrs": false,
  "minimum_entries": 1,
  "maximum_entries": 1000
}
```

Run `python3 scripts/generate_feeds.py` locally or run **Update SonicWall DEAG feeds** from the **Actions** tab. Failed downloads or validation do not replace the last valid published file.
