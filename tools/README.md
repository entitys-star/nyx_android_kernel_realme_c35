# Recovery preparation tools

## Stage the stock recovery runtime and DTB

Run from the root of this repository with the matching stock `vendor_boot.img` and Python 3. The ramdisk extractor requires the `lz4` Python package; the staging step also requires `cpio`.

```sh
python3 -m pip install --user lz4
python3 tools/prepare_vendor_ramdisk.py /path/to/vendor_boot.img
```

The staging script now performs both required extraction steps:

- writes the complete DTB payload to `device/realme/ums9230_nico/prebuilt/dtb.img`, preserving the Android DT table if present;
- populates `device/realme/ums9230_nico/recovery/root` with the reviewed stock recovery runtime, including the module files and recovery module-load list, while refusing to copy the stock `init.rc`.

For the inspected RMX3511T2_13.F.73 image, the DTB payload is at offset 24,698,880, size 163,976 bytes, and begins with Android DT table magic `d7b7ab1e`.

## Separate DTB extraction

If only the DTB is needed, run:

```sh
python3 tools/extract_vendor_boot_dtb.py /path/to/vendor_boot.img
```

Do not assume the device tree is build-ready or flashable after staging. Review the generated recovery root, fstab, SELinux policy handling, AVB/rollback configuration, and actual recovery boot behavior first.
