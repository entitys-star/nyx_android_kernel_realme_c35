#!/usr/bin/env python3
"""Decode an Android legacy-LZ4 vendor ramdisk from a vendor_boot v3/v4 image.

The output is a newc CPIO archive; extract it with:
    mkdir ramdisk-root && cd ramdisk-root && cpio -idm --no-absolute-filenames < ../vendor_ramdisk.cpio
Requires Python package lz4 (pip install lz4).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

MAGIC = b"VNDRBOOT"
LZ4_LEGACY_MAGIC = bytes.fromhex("02214c18")
CPIO_MAGICS = (b"070701", b"070702")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_legacy_lz4(payload: bytes) -> bytes:
    try:
        import lz4.block
    except ImportError as exc:
        raise SystemExit("error: install the Python lz4 package: python3 -m pip install lz4") from exc
    if not payload.startswith(LZ4_LEGACY_MAGIC):
        raise ValueError(f"unsupported ramdisk compression magic: {payload[:4].hex()}")
    output = bytearray()
    offset = len(LZ4_LEGACY_MAGIC)
    block_index = 0
    while offset < len(payload):
        if offset + 4 > len(payload):
            raise ValueError("truncated legacy-LZ4 block header")
        block_size_word = struct.unpack_from("<I", payload, offset)[0]
        offset += 4
        if block_size_word == 0:
            break
        uncompressed = bool(block_size_word & 0x80000000)
        block_size = block_size_word & 0x7fffffff
        end = offset + block_size
        if block_size == 0 or end > len(payload):
            raise ValueError(f"invalid legacy-LZ4 block {block_index}")
        block = payload[offset:end]
        offset = end
        if uncompressed:
            decoded = block
        else:
            try:
                decoded = lz4.block.decompress(block, uncompressed_size=8 * 1024 * 1024)
            except Exception as exc:
                raise ValueError(f"failed to decode legacy-LZ4 block {block_index}") from exc
        output.extend(decoded)
        block_index += 1
    if offset != len(payload):
        raise ValueError(f"legacy-LZ4 stream ended at {offset}, expected {len(payload)} bytes")
    if not any(output.startswith(magic) for magic in CPIO_MAGICS):
        raise ValueError("decoded payload does not begin with a newc CPIO magic")
    return bytes(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor_boot", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=Path("vendor_ramdisk.cpio"))
    args = parser.parse_args()
    image = args.vendor_boot.read_bytes()
    if len(image) < 2128 or image[:8] != MAGIC:
        raise SystemExit("error: input is not a complete Android vendor_boot image")
    version, page_size = struct.unpack_from("<II", image, 8)
    if version not in (3, 4) or page_size == 0 or page_size & (page_size - 1):
        raise SystemExit("error: unsupported vendor_boot version or invalid page size")
    ramdisk_size = struct.unpack_from("<I", image, 24)[0]
    start, end = page_size, page_size + ramdisk_size
    if ramdisk_size == 0 or end > len(image):
        raise SystemExit("error: vendor ramdisk range is invalid")
    compressed = image[start:end]
    decoded = decode_legacy_lz4(compressed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(decoded)
    print(json.dumps({
        "image_sha256": sha256(image),
        "ramdisk_offset": start,
        "compressed_size": len(compressed),
        "compressed_sha256": sha256(compressed),
        "cpio_size": len(decoded),
        "cpio_sha256": sha256(decoded),
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
