# TWRP device tree — Realme C35 (RMX3511)

**Status: incomplete bring-up scaffold. No image has been built or boot-tested.**

Target firmware: `RMX3511T2_13.F.73`, Android 13, device identity `ums9230_nico`.

## Layout

- `BoardConfig.mk`: parsed vendor_boot v4 offsets, vendor_boot output size, and TWRP settings.
- `twrp_ums9230_nico.mk`: product target.
- `recovery/root/system/etc/recovery.fstab`: copied from the stock vendor ramdisk as a starting point; must be reviewed for TWRP mount/decryption behavior.
- `prebuilt/dtb.img`: must be extracted byte-for-byte from the stock `vendor_boot.img` before building.
- `recovery/root/`: must contain the required stock vendor ramdisk runtime and recovery init/ueventd/module/SELinux files, generated from the exact stock image.

## Build blockers

1. Stage `prebuilt/dtb.img` and stock vendor ramdisk support files from the matching firmware.
2. Confirm the correct DTBO overlay/panel identity. The overlays indicate 720×1600 coordinates and include FocalTech-specific properties, but the exact selected overlay is not yet proven.
3. Find the FT8756 firmware blob required by the touch driver; it was not found in the stock vendor ramdisk.
4. Resolve AVB: the stock vbmeta chain uses rollback-index location 18 for vendor_boot; do not use the generator's generic location 0 without proof.
5. Validate data decryption, dynamic partition mounting, USB/ADB, and bootloader recovery selection.

This tree intentionally contains no kernel source or kernel build workflow. The stock kernel stays in the original `boot.img`; the intended output is a rebuilt `vendor_boot.img`.
