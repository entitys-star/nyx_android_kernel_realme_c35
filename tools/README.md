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

## Build through GitHub Actions

The workflow `.github/workflows/build-twrp-vendor-boot.yml` is manually triggered from the `twrp-rmx3511-research` branch. It uses the TWRP `twrp-12.1` manifest, stages the matching stock runtime, and requests the `vendorbootimage` target. The expected output is a rebuilt `vendor_boot.img`, not a standalone recovery partition image.

1. Create a GitHub Release in this repository and attach the original `vendor_boot.img` from firmware `RMX3511T2_13.F.73` as a release asset named `vendor_boot.img`. The workflow verifies its SHA-256 against the inspected stock image, so a repacked or different firmware image will be rejected.
2. Open **Actions → Build TWRP vendor_boot (RMX3511) → Run workflow** and select branch `twrp-rmx3511-research`.
3. Paste the release asset's direct download URL into `vendor_boot_url` and run it.
4. Download the `rmx3511-twrp-vendor-boot` artifact from the run. If the build fails, inspect the run log and the uploaded `build.log`.

The workflow has not yet been executed successfully. GitHub-hosted runner disk limits, manifest sync issues, TWRP make-target compatibility, AVB/rollback behavior, and on-device boot/touch/decryption are not yet validated. A successful build alone would not establish that the image is safe to flash.

## Separate DTB extraction

If only the DTB is needed, run:

```sh
python3 tools/extract_vendor_boot_dtb.py /path/to/vendor_boot.img
```

Do not assume the device tree is build-ready or flashable after staging. Review the generated recovery root, fstab, SELinux policy handling, AVB/rollback configuration, and actual recovery boot behavior first.
