#!/usr/bin/env python3
"""Extract the complete DTB payload from a stock Android vendor_boot v3/v4 image.

The Android DT table (if present) is preserved as-is. This matters because the
payload can contain a table of FDT entries rather than one raw flattened tree.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
from pathlib import Path

MAGIC = b"VNDRBOOT"


def align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor_boot", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("device/realme/ums9230_nico/prebuilt/dtb.img"),
    )
    args = parser.parse_args()

    data = args.vendor_boot.read_bytes()
    if data[:8] != MAGIC:
        raise SystemExit("error: input does not start with VNDRBOOT")
    if len(data) < 2112:
        raise SystemExit("error: truncated vendor_boot header")

    version, page_size = struct.unpack_from("<II", data, 8)
    if version not in (3, 4):
        raise SystemExit(f"error: unsupported vendor_boot header version {version}")
    if page_size == 0 or page_size & (page_size - 1):
        raise SystemExit(f"error: invalid page size {page_size}")

    ramdisk_size = struct.unpack_from("<I", data, 24)[0]
    header_size = struct.unpack_from("<I", data, 2096)[0]
    dtb_size = struct.unpack_from("<I", data, 2100)[0]
    if header_size < (2128 if version == 4 else 2112) or header_size > page_size:
        raise SystemExit(f"error: invalid header size {header_size}")

    dtb_offset = page_size + align(ramdisk_size, page_size)
    end = dtb_offset + dtb_size
    if dtb_size == 0 or end > len(data):
        raise SystemExit(
            f"error: DTB range [{dtb_offset}, {end}) is outside image size {len(data)}"
        )

    payload = data[dtb_offset:end]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    print(f"vendor_boot header: v{version}, page size {page_size}")
    print(f"DTB payload: offset={dtb_offset} size={dtb_size}")
    print(f"wrote: {args.output}")
    print(f"sha256: {digest}")
    if payload[:4] == bytes.fromhex("d7b7ab1e"):
        total = struct.unpack_from(">I", payload, 4)[0]
        count = struct.unpack_from(">I", payload, 20)[0]
        print(f"Android DT table: declared_size={total}, entries={count}")
    elif payload[:4] == bytes.fromhex("d00dfeed"):
        print("DTB payload begins with a raw FDT")
    else:
        print(f"warning: unrecognized DTB payload magic {payload[:4].hex()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
