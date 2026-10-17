#!/usr/bin/env python3
"""Stage the stock Unisoc vendor runtime required by a TWRP vendor_boot tree.

This is intentionally not a full device-tree generator. It preserves required
vendor files and excludes stock init.rc so it cannot replace TWRP's init.
Requires Python lz4, cpio, and tools/extract_vendor_boot_ramdisk.py.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_FILES = re.compile(
    r"^(?:sepolicy|.*_contexts|init\.recovery\..*\.rc|ueventd.*\.rc|.*\.sh)$"
)


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination, follow_symlinks=True)


def copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, symlinks=True)


def strip_avb_fstab(source: Path, destination: Path) -> None:
    content = source.read_text(encoding="utf-8")
    content = re.sub(r",avb_keys=[^,\s]+", "", content)
    content = re.sub(r",avb(?:=[^,\s]+)?", "", content)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vendor_boot", type=Path)
    parser.add_argument("--device-tree", type=Path,
                        default=Path("device/realme/ums9230_nico"))
    args = parser.parse_args()
    source_image = args.vendor_boot.resolve()
    device_tree = args.device_tree.resolve()
    if not source_image.is_file():
        raise SystemExit(f"error: image not found: {source_image}")
    if not (Path(__file__).with_name("extract_vendor_boot_ramdisk.py")).is_file():
        raise SystemExit("error: extract_vendor_boot_ramdisk.py must be beside this script")

    with tempfile.TemporaryDirectory(prefix="rmx3511-vendor-ramdisk-") as temp:
        temp_path = Path(temp)
        archive = temp_path / "vendor_ramdisk.cpio"
        extractor = Path(__file__).with_name("extract_vendor_boot_ramdisk.py")
        subprocess.run([sys.executable, str(extractor), str(source_image),
                        "--output", str(archive)], check=True, stdout=subprocess.DEVNULL)
        unpacked = temp_path / "stock-root"
        unpacked.mkdir()
        with archive.open("rb") as stream:
            subprocess.run(["cpio", "-idm", "--quiet", "--no-absolute-filenames"],
                           cwd=unpacked, stdin=stream, check=True)

        target = device_tree / "recovery" / "root"
        first_stage = unpacked / "first_stage_ramdisk"
        if first_stage.is_dir():
            for source in first_stage.rglob("*"):
                if source.is_file() and source.name.startswith("fstab."):
                    relative = source.relative_to(unpacked)
                    strip_avb_fstab(source, target / relative)

        copy_tree(unpacked / "lib" / "modules", target / "lib" / "modules")
        for relative in ("system/etc/recovery.fstab", "system/etc/ueventd.rc"):
            source = unpacked / relative
            if source.is_file():
                if source.name == "recovery.fstab":
                    strip_avb_fstab(source, target / relative)
                else:
                    copy_file(source, target / relative)

        for source in unpacked.iterdir():
            if source.is_file() and ROOT_FILES.fullmatch(source.name):
                copy_file(source, target / source.name)

        copy_tree(unpacked / "vendor", target / "vendor")
        for relative in ("system/etc/vintf/manifest.xml",
                         "system/etc/twrp.flags",
                         "system/etc/ueventd.rc"):
            source = unpacked / relative
            if source.is_file():
                copy_file(source, target / relative)

        if (target / "init.rc").exists():
            raise SystemExit("error: target contains init.rc; refusing to leave stock init.rc in TWRP root")
        if not (target / "system/etc/recovery.fstab").is_file():
            raise SystemExit("error: stock recovery.fstab was not staged")
        if not (target / "lib/modules/modules.load.recovery").is_file():
            print("warning: modules.load.recovery was not found; audit module loading", file=sys.stderr)

    print(f"Staged stock vendor runtime into: {device_tree / 'recovery' / 'root'}")
    print("Review the generated tree, SELinux policy handling, and TWRP fstab before building.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
