# Realme C35 RMX3511 — TWRP / Recovery research

> Status: reconnaissance only. No TWRP image has been built or tested. Do not flash an image based on these notes.

## Scope and separation from Nyx

This document tracks the recovery/TWRP investigation for the Realme C35. It is kept on the `twrp-rmx3511-research` branch so it does not mix with the Nyx kernel work on `dev`. Kernel/KernelSU work is a separate track.

## Device identifiers collected so far

- Model: `RMX3511`
- Device: `RE87BAL1`
- Product: `RMX3511T2`
- Board/platform: `ums9230_nico` / `ums9230`
- Firmware reported by the running system: `RMX3511T2_13.F.73`
- Running system fingerprint reported earlier: `realme/RMX3511T2/RE87BAL1:13/TP1A.220624.014/R.202408010030:user/release-keys`
- Recovery ramdisk `prop.default` identifies `RMX3511`, `RE87BAL1`, `ums9230_nico`; it reports Android 12 / SDK 31 fingerprints and build ID `R.202408010030`.
- Bootloader is unlocked.
- Layout is dynamic-partition capable; device reports A/B support, current slot `a`, and two slots. However, observed logical B partitions have size zero, so the exact slot/update layout needs further validation.
- No standalone `recovery` partition was found in the reported by-name partition list.
- `boot_a` and `boot_b`: 64 MiB each.
- `vendor_boot_a` and `vendor_boot_b`: 100 MiB each.
- `dtbo_a` and `dtbo_b`: 8 MiB each.
- `super`: about 7.9 GiB (reported size `0x1F4000000`).
- Platform appears to be Unisoc (`ums9230`; firmware package includes `ums9230_nico.xml`).

## Stock firmware images inspected

The local stock firmware package contains:
- `boot.img`
- `vendor_boot.img`
- `dtbo.img`
- `super.img`
- several vbmeta images
- `ums9230_nico.xml` and Unisoc firmware configuration files

The package location on the investigator's machine was `spreadtrum_flash-main/unpac/ROM/`; this is a local path, not a repository path.

### boot.img

Parsed with `unpack_bootimg`:
- Android boot image magic: `ANDROID!`
- Header version: 4
- Kernel size: 31,584,768 bytes
- Ramdisk size: 1,469,860 bytes
- OS version: Android 13
- OS security patch level: 2024-07
- Signature size: 0

Extracted files: kernel and ramdisk.

### vendor_boot.img

Parsed with `unpack_bootimg`:
- Magic: `VNDRBOOT`
- Header version: 4
- Page size: 4096
- Vendor ramdisk total size: 24,694,046 bytes
- DTB size: 163,976 bytes
- One vendor ramdisk table entry, type `0x1`, no board name
- Vendor cmdline: `console=ttyS1,115200n8 buildvariant=user`

The vendor ramdisk was extracted and its LZ4-compressed payload decoded to CPIO. The CPIO contains a stock recovery environment, including:
- `system/bin/recovery`
- `system/etc/recovery.fstab`
- `system/etc/recovery.tmpfsdata.fstab`
- `init.recovery.common.rc`
- per-board init stubs such as `init.recovery.ums9230_nico.rc`
- `lib/modules/modules.load.recovery`
- Unisoc kernel modules

This is the stock recovery environment, not TWRP.

## Device variant confirmation

The extracted `prop.default` contains:
- `ro.product.system.model=RMX3511`
- `ro.product.system.device=RE87BAL1`
- `ro.product.board=ums9230_nico`
- `ro.board.platform=ums9230`
- `ro.build.flavor=ums9230_nico_Natv-user`
- `ro.boot.dynamic_partitions=true`

This is direct evidence that the extracted recovery ramdisk configuration identifies itself as RMX3511 / RE87BAL1 / ums9230_nico.

The file `init.recovery.ums9230_nico.rc` is only 73 bytes and contains:
```rc
#add for board init.rc for recovery mode
import /init.recovery.common.rc
```
Thus the board-specific stub imports the common recovery init script.

## Findings from fstab files

### `first_stage_ramdisk/fstab.ums9230_nico`

Entries include:
- `system` mounted at `/system` as EROFS or ext4, read-only, logical, slot-selected and AVB-protected.
- `system_ext`, `vendor`, `product`, `vendor_dlkm` as logical EROFS read-only partitions, with relevant AVB metadata.
- `metadata` at `/metadata` as ext4, with `formattable` and `first_stage_mount` flags.

Notably, this first-stage fstab does not contain a `/data` entry.

### `system/etc/recovery.fstab`

Relevant entries:
- Many physical Unisoc/vendor partitions are referenced by `/dev/block/by-name/*`.
- `system`, `system_ext`, `vendor`, `product`, `vendor_dlkm` are logical partitions; `system` has EROFS and ext4 alternatives.
- `metadata` uses ext4.
- `/data` points to `/dev/block/by-name/userdata`, uses F2FS, and includes file-based encryption parameters, including:
  - `fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized`
  - `keydirectory=/metadata/vold/metadata_encryption`
  - `inlinecrypt`
  - `formattable`
- `/cache` has ext4 and F2FS alternatives.
- `/mnt/vendor` maps to the `prodnv` partition.
- `/storage/sdcard0` points to `/dev/block/mmcblk1p1`.

The presence of F2FS support alone does not establish that a future TWRP build can decrypt user data. Decryption support must be investigated and tested separately.

### `system/etc/recovery.tmpfsdata.fstab`

This file contains entries for vendor/physical partitions and read-only system partitions. It does **not** contain the `userdata` or `metadata` entries found in `recovery.fstab`. The common init script invokes:
```rc
mount_all /etc/recovery.tmpfsdata.fstab
mount tmpfs tmpfs /data mode=0777
```
This is evidence that the stock recovery has a mode in which it mounts a temporary filesystem on `/data`; the exact trigger and purpose still need to be traced before copying any such behavior into TWRP.

## Findings from `init.recovery.common.rc`

The grep review showed:
- ConfigFS USB gadget setup.
- USB functions for ADB and Fastboot.
- A recovery service class started when `ro.bootmode=recovery`.
- Several triggers that mount `recovery.tmpfsdata.fstab` and then mount tmpfs on `/data`.

These details may be useful for understanding stock recovery behavior, but they should not be copied wholesale into TWRP without tracing their triggers and dependencies.

## Important uncertainties / next tasks

1. Inspect the full relevant sections of `init.recovery.common.rc`, especially the triggers around lines 250–340 and 400 onward, to identify exactly when tmpfs-data mode is selected.
2. Inspect `ums9230_nico.xml` and `partition_fw.xml` to corroborate partition naming and physical layout against the live device's by-name map.
3. Compare the extracted boot/vendor_boot images with the exact installed firmware. The reported running system is Android 13, while vendor recovery properties report Android 12 / SDK 31; determine whether this is an intentional mixed-version firmware layout or a package mismatch.
4. Inspect the DTB and DTBO data and identify display, touch, USB, storage, and recovery-related device-tree nodes.
5. Determine the appropriate TWRP branch/version and build method for Android boot header v4, vendor_boot v4, Unisoc ums9230, and the device's partition layout.
6. Create a device tree with verified partition paths, fstab, init configuration, recovery UI/display/touch settings, and required proprietary dependencies where applicable.
7. Build an image and validate it without flashing first. Establish the correct boot method and recovery path before attempting any write operation.
8. Investigate F2FS and encrypted `/data` decryption as a separate compatibility task.

## Safety notes

- Do not flash a generic `vendor_boot.img` or a recovery image for another model.
- Do not format `metadata` or `userdata` as part of reconnaissance.
- Keep original stock `boot.img`, `vendor_boot.img`, `dtbo.img`, vbmeta images, and a verified restoration method available before any device-side test.
- All findings above are based on local command output gathered so far; anything marked uncertain still needs confirmation.
