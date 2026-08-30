"""Generate the cloud egress-guard env values from the LOCAL token map.

    python -m house.export_egress_hashes

Prints EGRESS_SALT and EGRESS_ALIAS_HASHES for the Cloud Run service config.
Only salted SHA-256 hashes leave this machine — the cloud can detect a leaking
family name without ever holding one."""

from __future__ import annotations

from house import config, scrub


def main() -> None:
    tmap = scrub.load_map(config.TOKEN_MAP_PATH)
    hashes = scrub.salted_alias_hashes(tmap)
    print(f"EGRESS_SALT={tmap.salt}")
    print(f"EGRESS_ALIAS_HASHES={','.join(hashes)}")
    print(f"# {len(hashes)} hashes from {config.TOKEN_MAP_PATH.name} — no plaintext exported")


if __name__ == "__main__":
    main()
