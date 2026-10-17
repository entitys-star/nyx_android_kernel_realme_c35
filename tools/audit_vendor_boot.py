#!/usr/bin/env python3
"""Audit and extract the DTB table and vendor ramdisk from Android vendor_boot v3/v4."""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path

MAGIC = b"VNDRBOOT"
DT_TABLE_MAGIC = bytes.fromhex("d7b7ab1e")

def align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor_boot", type=Path)
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("vendor_boot_audit"))
    args = parser.parse_args()
    image = args.vendor_boot.read_bytes()
    if len(image) < 2128 or image[:8] != MAGIC:
        raise SystemExit("error: input is not a complete Android vendor_boot image")
    version, page_size = struct.unpack_from("<II", image, 8)
    if version not in (3, 4):
        raise SystemExit(f"error: unsupported vendor_boot header version {version}")
    if page_size == 0 or page_size & (page_size - 1):
        raise SystemExit(f"error: invalid page size {page_size}")
    ramdisk_size = struct.unpack_from("<I", image, 24)[0]
    header_size = struct.unpack_from("<I", image, 2096)[0]
    dtb_size = struct.unpack_from("<I", image, 2100)[0]
    if header_size < (2128 if version == 4 else 2112) or header_size > page_size:
        raise SystemExit(f"error: invalid header size {header_size}")
    ramdisk_offset = page_size
    ramdisk_end = ramdisk_offset + ramdisk_size
    dtb_offset = align(ramdisk_end, page_size)
    dtb_end = dtb_offset + dtb_size
    if ramdisk_size == 0 or ramdisk_end > len(image):
        raise SystemExit("error: vendor ramdisk range is invalid")
    if dtb_size == 0 or dtb_end > len(image):
        raise SystemExit("error: DTB range is invalid")
    ramdisk, dtb = image[ramdisk_offset:ramdisk_end], image[dtb_offset:dtb_end]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ramdisk_path = args.output_dir / "vendor_ramdisk.lz4"
    dtb_path = args.output_dir / "dtb.img"
    manifest_path = args.output_dir / "manifest.json"
    ramdisk_path.write_bytes(ramdisk)
    dtb_path.write_bytes(dtb)
    metadata: dict[str, object] = {
        "input": str(args.vendor_boot), "image_size": len(image),
        "image_sha256": sha256(image), "header_version": version,
        "page_size": page_size, "header_size": header_size,
        "vendor_ramdisk_offset": ramdisk_offset, "vendor_ramdisk_size": ramdisk_size,
        "vendor_ramdisk_sha256": sha256(ramdisk), "dtb_offset": dtb_offset,
        "dtb_size": dtb_size, "dtb_sha256": sha256(dtb),
        "vendor_cmdline": image[28:2048].split(bytes([0]), 1)[0].decode("ascii", "replace"),
    }
    if version == 4:
        table_size, table_count, table_entry_size = struct.unpack_from("<III", image, 2112)
        bootconfig_size = struct.unpack_from("<I", image, 2124)[0]
        metadata.update({"vendor_ramdisk_table_size": table_size,
                         "vendor_ramdisk_table_entries": table_count,
                         "vendor_ramdisk_table_entry_size": table_entry_size,
                         "bootconfig_size": bootconfig_size})
    if dtb[:4] == DT_TABLE_MAGIC:
        total_size, dt_header_size, entry_size, entry_count = struct.unpack_from(">IIII", dtb, 4)
        metadata["android_dt_table"] = {"declared_size": total_size,
            "header_size": dt_header_size, "entry_size": entry_size, "entry_count": entry_count}
    manifest_path.write_text(json.dumps(metadata, indent=2) + chr(10), encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    print(f"Extracted ramdisk: {ramdisk_path}")
    print(f"Extracted DTB: {dtb_path}")
    print(f"Manifest: {manifest_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
