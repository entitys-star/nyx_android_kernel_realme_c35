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

## Follow-up: conditions for tmpfs `/data` mode

The inspected range of `init.recovery.common.rc` (lines 245–345 in the extracted file) shows the two previously found `mount_all /etc/recovery.tmpfsdata.fstab` + `mount tmpfs tmpfs /data mode=0777` sequences under explicit boot-mode property triggers:

- `on property:ro.bootmode=cali`
- `on property:ro.bootmode=factorytest`

The `cali` block also configures the USB gadget as a serial/vser port, creates temporary directories under `/data`, starts the `cali` class, loads vendor GPU modules from `/mnt/product/socko/`, and starts vendor logging/modem services. The `factorytest` block sets USB to `adb,vser,gser`, mounts the same temporary `/data`, creates a `/system` symlink to `/system_root/system`, and prepares test-related directories and device permissions.

**Interpretation:** the observed tmpfs `/data` behavior belongs to calibration/factory-test modes, not evidence of the normal user-facing recovery path. Do not copy this tmpfs mounting behavior into TWRP as a default. The exact normal recovery boot path still needs inspection in the remaining init script, especially its triggers and service definitions.

This finding is based on the user's terminal output of `sed -n '245,345p' init.recovery.common.rc`; it does not establish how all firmware variants behave.

## Follow-up: common init actions and recovery-mode trigger

The user inspected lines 1–114 and 345–430 of `init.recovery.common.rc`.

Confirmed from the shown source:
- Services include `healthd`, a one-shot helper `create_splloader_dual_slot_byname_path.sh`, modem control services for `cali` and `factorytest`, and vendor logging/network/GPS-related services.
- The `on init` action sets `PATH` and `SECONDARY_STORAGE`, creates storage mount points and symlinks, adjusts permissions on Unisoc diagnostic nodes, creates several `/data/...` directories, loads three vendor GPU modules from `/mnt/product/socko/`, adjusts GNSS permissions, starts vendor disk/logging services, and ends with `trigger factorytest`.
- The tail contains `on property:ro.bootmode=factorytest && property:ro.debuggable=0`, which sets USB config to `vser`.
- Earlier inspection of lines around 214 found `on property:ro.bootmode=recovery` followed by `class_start recovery`.
- The temporary tmpfs `/data` mount was seen under the explicit `cali` and `factorytest` boot-mode property actions, not in the displayed generic `on init` range.

Interpretation and caveats:
- This stock recovery init file contains substantial Unisoc/Realme factory and hardware-test support, so not every vendor action should be carried over into TWRP.
- The displayed `on init` action creates paths beneath `/data` but this excerpt alone does not show the normal recovery data-mount sequence; creating a directory is not proof that userdata is mounted.
- The exact effect of `trigger factorytest` and the normal recovery class/service contents should be checked against the complete set of action headers and service declarations before drawing further conclusions.

## Follow-up: complete action/service header inventory

The user ran:
```
grep -nE '^(on |service |import |mount_all|mount |class_start|start recovery|trigger )' init.recovery.common.rc
```

The visible action/service headers are:
- Services: `healthd` (line 5), `create_splloader_dual_slot_byname_path` (9), calibration/factory modem/logging/network/console/GPS services (16–77).
- Actions: `on init` (82), `on boot` (155), `on fs` (165), `on post-fs-data` (169), `on property:ro.debuggable=1` (211), `on property:ro.bootmode=recovery` (214), USB config triggers (217, 240), and boot-mode-specific `cali` (261), `factorytest` (328), and `factorytest && ro.debuggable=0` (408).
- No top-level `import`, `mount_all`, `mount`, `class_start`, `start recovery`, or `trigger` lines are reported by this grep pattern because those commands occur indented inside actions; the pattern intentionally only matches column-one headers. The file's board-specific init stub imports this common file, and the recovery boot-mode action at line 214 starts the `recovery` class.

Next investigation should inspect the contexts around `on boot`, `on fs`, `on post-fs-data`, `ro.debuggable=1`, and `ro.bootmode=recovery` (roughly lines 145–225) to understand mounts and startup without confusing nested commands with action headers.

## Follow-up: normal recovery startup and generic filesystem actions

The user inspected lines 145–225 of `init.recovery.common.rc`.

Confirmed from the shown excerpt:
- `on boot` enables ConfigFS USB gadget mode, writes `force_ro=0` for `/sys/block/mmcblk0boot0` and `mmcblk0boot1`, and changes permissions for several battery charging controls.
- `on fs` creates `/data/misc/bluetooth`.
- `on post-fs-data` changes ownership/mode of `/data`, runs `restorecon /data`, creates Bluetooth, Wi-Fi, DHCP, and vendor logging directories, and writes Wi-Fi settings under `/data/vendor/wifi`.
- `on property:ro.debuggable=1` enables a Unisoc diagnostic parameter.
- `on property:ro.bootmode=recovery` runs `class_start recovery`.
- A USB ConfigFS trigger handles the combined `adb,vser,gser` configuration.

Interpretation/caution:
- These actions assume paths under `/data` are usable when their triggers run, but this excerpt does not itself show which block device or filesystem mounted there. The stock recovery's separate `recovery.fstab` defines a F2FS userdata entry, but actual normal-mode mount ordering must be established from the full init and recovery binary behavior.
- The `on boot` writes that disable read-only protection on eMMC boot partitions are vendor-specific and potentially sensitive; they are not instructions to reproduce blindly in TWRP.
- The stock `class_start recovery` trigger confirms the class name, but the shown file does not declare a `service ... class recovery` entry. Service/class declarations may be elsewhere in the extracted ramdisk or in the recovery binary.

## Follow-up: recovery service declared in ramdisk init.rc

The user's recursive grep found the actual service declaration in both `./etc/init/hw/init.rc` and the equivalent symlinked path `./system/etc/init/hw/init.rc`:
```
service recovery /system/bin/recovery
```
at line 72. It also found:
```
service adbd /system/bin/adbd --root_seclabel=u:r:su:s0 --device_banner=recovery
```
at line 76.

The grep did not show a `class recovery` declaration in this output, but `init.recovery.common.rc` starts that class when `ro.bootmode=recovery`. The service stanza's remaining lines and any imported init files must be inspected before concluding its class/options or exact startup ordering. Duplicate paths are due to symlinked layout; the `odm`/ `vendor_dlkm` missing-target warnings are from dangling symlinks, not proof the search is incomplete in ordinary files. Binary-match notices are expected when recursive grep scans executables.

Next inspect the service block and nearby init imports, e.g. `sed -n '55,95p' etc/init/hw/init.rc` from the current extracted root.

## Follow-up: exact recovery/adbd service stanzas

The user inspected `etc/init/hw/init.rc`, lines 55–95. Exact declarations:
```
service recovery /system/bin/recovery
    socket recovery stream 422 system system
    seclabel u:r:recovery:s0

service adbd /system/bin/adbd --root_seclabel=u:r:su:s0 --device_banner=recovery
    disabled
    socket adbd stream 660 system system
    seclabel u:r:adbd:s0

service fastbootd /system/bin/fastbootd
    disabled
    group system
    seclabel u:r:fastbootd:s0
```
A following action says `on property:service.adb.root=1` then `restart adbd`; an `on fs && property:sys.usb.configfs=1` action begins configuring the USB gadget.

Interpretation:
- `recovery` service has a Unix stream socket named `recovery` with mode 422 and system ownership, and SELinux domain `u:r:recovery:s0`.
- `adbd` and `fastbootd` are declared `disabled` (not started automatically by their service class alone; they need an explicit start/restart/property path).
- The `service recovery ...` line is syntax inside Android's init configuration, not a command to run in the host Fish shell. The user's attempt to execute it directly resulted in `fish: Unknown command: service`; no device state was changed.
- The exact mechanism that starts the recovery service (including whether the recovery binary self-starts or is started by init service class handling) still needs verification from the remaining init configuration and recovery class logic. Do not infer it from this stanza alone.

## Follow-up: stock recovery executable format

The user ran `file system/bin/recovery` from the extracted vendor ramdisk root. Output:
```
system/bin/recovery: ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /system/bin/linker64, for Android 31, BuildID[md5/uuid]=767eda7548a28997c0d70befea607447, stripped
```

Confirmed:
- 64-bit ARM/AArch64 Android PIE executable.
- Dynamically linked with Android linker at `/system/bin/linker64`.
- ELF metadata reports Android API/platform version 31 (Android 12-era build target), and the binary is stripped.
- This is consistent with the earlier `prop.default` values identifying the extracted recovery ramdisk as `ums9230_nico_Natv-user` / Android 12, while the currently installed system reports Android 13. This version mismatch remains unresolved and means we must verify that all firmware images belong to a compatible package before basing a build on them.
- `file` output alone does not reveal required shared libraries or prove source availability. Next inspect dynamic dependencies with an Android-aware ELF tool such as `llvm-readelf -d system/bin/recovery` (or `readelf -d` if installed); do not try to execute the Android binary on the host.

## Follow-up: stock recovery dynamic dependencies

The user ran `llvm-readelf -d system/bin/recovery`. The Android 31 AArch64 PIE binary declares these `DT_NEEDED` dependencies:
- Android HALs: `android.hardware.health@2.0.so`, `android.hardware.boot@1.0.so`, `android.hardware.boot@1.1.so`
- Android platform libraries: `libcutils.so`, `liblp.so`, `libprotobuf-cpp-lite.so`, `libbase.so`, `libbootloader_message.so`, `libcrypto.so`, `libext4_utils.so`, `libfs_mgr.so`, `libfusesideload.so`, `libhidl-gen-utils.so`, `libhidlbase.so`, `liblog.so`, `libselinux.so`, `libtinyxml2.so`, `libutils.so`, `libz.so`, `libziparchive.so`, `librecovery_ui.so`, `libc++.so`, `libc.so`, `libm.so`, `libdl.so`.
- ELF flags include `BIND_NOW` and `NOW PIE`; binary uses Android-specific relocation tags.

Interpretation:
- This is a platform recovery executable linked against Android recovery/HAL and platform libraries, not a standalone Linux binary that can simply be copied into a generic recovery ramdisk.
- For TWRP, use the TWRP source/build system and a device tree that supplies the correct device-specific build configuration, fstab, init, kernel/DTB handling, and required proprietary/vendor compatibility where applicable. Reusing the stock binary alone is not a viable substitute for a TWRP build.
- This dependency list alone does not establish which of these libraries are present in the extracted ramdisk or whether the stock executable can boot against the current Android 13 vendor/system combination. The previously noted Android 12/13 mismatch remains unresolved.


## Firmware XML and image inventory (2026-10-17)

Source checked locally: `ROM/ums9230_nico.xml` and the extracted `ROM/` directory.

The XML partition table declares:
- `boot_a`, `boot_b`: 64 MiB each
- `vendor_boot_a`, `vendor_boot_b`: 100 MiB each
- `dtbo_a`, `dtbo_b`: 8 MiB each
- `super`: 8000 MiB
- `metadata`: 16 MiB
- `userdata`: size sentinel `0xFFFFFFFF`
- separate A/B entries for `vbmeta`, `vbmeta_system`, `vbmeta_system_ext`, `vbmeta_vendor`, `vbmeta_product`, `vbmeta_odm`, and `avbmeta_rs`.

In the XML download-file section:
- `BOOT` (`CODE2`) maps to block `boot_a`; description: “Kernel image file”.
- `VENDOR_BOOT` (`CODE2`) maps to `vendor_boot_a`; description: “Kernel vendor_boot image file”.
- `DTBO` (`CODE2`) maps to `dtbo_a`.
- `Super` (`YAFFS_IMG2`) maps to `super`.
- `VBMETA` and the named vbmeta entries map to their corresponding `*_a` blocks.
- `UserData` (`YAFFS_IMG2`) maps to `userdata` and has `groupflag="1"`.

The `Base` and `Size` fields shown for these file entries are `0x0`; they do not establish the actual payload image sizes. The XML maps package file roles to blocks, but the file names alone do not prove a safe raw-flash mapping for every image.

Observed extracted `ROM/` files and approximate displayed sizes:
- `boot.img`: 67M
- `vendor_boot.img`: 105M
- `dtbo.img`: 8.4M
- `super.img`: 5.9G
- `vbmeta-sign.img`: 1.0M
- `vbmeta_system.img`: 4.1K
- `vbmeta_vendor.img`: 4.1K
- `vbmeta_product.img`: 2.4K
- `vbmeta_system_ext.img`: 2.4K
- also present: `vbmeta_odm` is declared by XML, but no correspondingly named `vbmeta_odm.img` appeared in the displayed directory listing.

The likely name-based correspondence is `boot.img`→`boot_a`, `vendor_boot.img`→`vendor_boot_a`, `dtbo.img`→`dtbo_a`, `super.img`→`super`, and the named vbmeta images to their corresponding vbmeta roles. Treat this as a package-role hypothesis, not authorization to flash them directly. In particular, `vbmeta-sign.img` is not interchangeable by name or size with the smaller partition-specific vbmeta images.

No separate `recovery` partition is declared in the examined partition list; the stock recovery environment is carried in the boot/vendor-boot arrangement. Further build work should continue from the stock boot and vendor_boot structures and the extracted recovery ramdisk, rather than assume a dedicated recovery partition.


## AVB metadata inspection (2026-10-17)

Ran `avbtool info_image` on `vbmeta-sign.img`, `vbmeta_system.img`, `vbmeta_vendor.img`, `vbmeta_product.img`, and `vbmeta_system_ext.img`.

Common properties reported for all five:
- Minimum libavb version 1.0
- Algorithm `SHA256_RSA4096`
- Rollback Index 1; Flags 0; Release String `avbtool 1.2.0`
- All begin with AVB magic `AVB0`.

`vbmeta-sign.img`:
- Public key SHA-1: `0b2c2a7ec06fb50c4a030b7d96a1282670bfc383`
- Contains chain partition descriptors for `boot` (rollback index location 1), `vendor_boot` (18), `dtbo` (6), `vbmeta_system` (2), `vbmeta_vendor` (4), `vbmeta_system_ext` (3), `vbmeta_product` (5), plus `l_modem`, `l_ldsp`, `l_gdsp`, `pm_sys`, and `l_agdsp`.
- Properties report boot, system, and vendor OS version 13 and security patch 2024-07-05.
- This is the root-style AVB metadata image in the package based on its chain descriptors; do not assume its filename is the raw partition name.

`vbmeta_system.img`:
- Public key SHA-1: `5ad58b3d49e09ebe9f4ac6f69e25271dec6d9e46`
- Properties identify system and system_ext as Android 13, fingerprint `realme/RMX3511/RE87BAL1:13/TP1A.220624.014/R.202408010030:user/release-keys`, patch 2024-07-05.
- Hashtree descriptors cover `system` (image size 3,066,585,088 bytes) and `system_ext` (564,166,656 bytes), SHA-256, 4096-byte data/hash blocks.

`vbmeta_vendor.img`:
- Public key SHA-1: `96ec51bfe0749fef522a74ed02e87c071111a2a8`
- Properties identify `vendor` and `vendor_dlkm` as Android 12, fingerprint `realme/RMX3511/RE87BAL1:12/SP1A.210812.016/S.R.202408010030:user/release-keys`, patch 2024-07-05.
- Hashtree descriptors cover `vendor` (image size 809,582,592 bytes) and `vendor_dlkm` (8,400,896 bytes).

`vbmeta_product.img`:
- Public key SHA-1: `f3e79cd4e3ca50703c546976d81eb6dd1d5a9c5b`
- Properties identify product as Android 13 with the same Android 13 fingerprint and 2024-07-05 patch.
- Hashtree descriptor covers `product` (image size 1,390,014,464 bytes).

`vbmeta_system_ext.img`:
- Public key SHA-1: `ca001596729cec10fcd4bbe70d070d801bfaf1fa`
- Unexpectedly, its descriptors report `vendor_dlkm` properties and a `vendor_dlkm` hashtree with image size 8,400,896 bytes, matching the descriptor values reported by `vbmeta_vendor.img`, despite its different public key and filename/partition role in the package XML.
- This is an anomaly to investigate, not proof that the file is corrupt or that the two images are interchangeable. Do not flash based on filename alone.

Important confirmed version split: the package's AVB properties describe system/system_ext/product as Android 13 but vendor/vendor_dlkm as Android 12, consistent with earlier stock recovery ramdisk properties and vendor fingerprint. This indicates a mixed-version system/vendor stack in the package and should be recorded as an observed fact; it does not by itself establish that the package is invalid.

These `avbtool info_image` results inspect metadata and descriptors; they do not by themselves verify the RSA signature against a trusted public key or prove that the currently installed phone uses these exact images.


## Existing public TWRP device-tree leads (2026-10-17)

Repository searches found two generated TWRP device-tree repositories for this exact model/platform:
- `twrpdtgen/android_device_realme_ums9230_nico` — initial commit 2023-07-10, generated by SebaUbuntu's TWRP device tree generator. README identifies RMX3511 / `ums9230_nico`. Tree: https://github.com/twrpdtgen/android_device_realme_ums9230_nico
- `SULeimanV/RE87BAL1_TWRP_TREE` — last inspected commit 2024-11-23. README identifies RMX3511 / `RE87BAL1`. Tree: https://github.com/SULeimanV/RE87BAL1_TWRP_TREE

Neither repository exposes a GitHub release in the checked releases API (both returned empty arrays); their existence is not proof that a working recovery image was built or tested on-device. Treat them as reference sources, not as verified flashable builds.

Both BoardConfig files set `BOARD_USES_RECOVERY_AS_BOOT := true`, use header version 4, target `ums9230`, and force a prebuilt kernel/DTB. Their configuration must be audited against this handset's actual firmware before reuse:
- Observed physical `boot_a` size is 64 MiB; the generated trees set `BOARD_BOOTIMAGE_PARTITION_SIZE := 104857600` (100 MiB), which matches this handset's `vendor_boot` size rather than its `boot` size.
- The generated trees hardcode `BOARD_SUPER_PARTITION_SIZE := 9126805504` (about 8.5 GiB) while this handset's XML declares `super` size 8000 MiB (8,388,608,000 bytes); this is a material mismatch.
- The `RE87BAL1_TWRP_TREE` partition list repeats `system` in `BOARD_REALME_DYNAMIC_PARTITIONS_PARTITION_LIST`; this looks like a config defect and must not be copied without correction.
- Both trees include `recovery.fstab`; the newer one includes EROFS and F2FS entries, while the older tree's system/vendor logical entries are ext4-only. Stock firmware fstab and current AVB descriptors are the primary evidence for this device.

The newer tree's `recovery.fstab` resembles the extracted stock recovery fstab in partition names, including F2FS `/data`, EROFS logical partitions, `/metadata`, and Unisoc modem/NV partitions. It should be diffed against the actual extracted fstab before reuse, especially encryption flags and logical/slot semantics. No tree from either repository should be flashed unchanged.


## Audit of the public device trees against the stock image layout (2026-10-17)

Source files read directly from GitHub:
- [SULeimanV/RE87BAL1_TWRP_TREE/BoardConfig.mk](https://github.com/SULeimanV/RE87BAL1_TWRP_TREE/blob/master/BoardConfig.mk)
- [SULeimanV/RE87BAL1_TWRP_TREE/recovery.fstab](https://github.com/SULeimanV/RE87BAL1_TWRP_TREE/blob/master/recovery.fstab)
- [twrpdtgen/android_device_realme_ums9230_nico/BoardConfig.mk](https://github.com/twrpdtgen/android_device_realme_ums9230_nico/blob/ums9230_nico_Natv-user-12-SP1A.210812.016-1605-release-keys/BoardConfig.mk)
- [twrpdtgen/android_device_realme_ums9230_nico/recovery.fstab](https://github.com/twrpdtgen/android_device_realme_ums9230_nico/blob/ums9230_nico_Natv-user-12-SP1A.210812.016-1605-release-keys/recovery.fstab)

### Device-tree assumptions that conflict with observed firmware

1. **Recovery placement is not established by either tree.** Both set `BOARD_USES_RECOVERY_AS_BOOT := true`. The actual stock package has no dedicated `recovery` partition; its 100 MiB `vendor_boot` image uses header v4 and contains a vendor ramdisk with the stock recovery executable, recovery fstab, and recovery init scripts. Therefore the generated setting cannot be accepted without confirming the TWRP build system's header-v4/vendor-ramdisk packaging behavior. The image must preserve the stock boot/vendor_boot split and place TWRP resources in the correct image. Do not infer that a normal recovery-as-boot image is correct merely because the device is A/B.
2. **Boot-image size mismatch needs firmware/version verification.** Both declare `BOARD_BOOTIMAGE_PARTITION_SIZE := 104857600` (100 MiB), while the inspected RMX3511T2_13.F.73 package and device report `boot_a` = 64 MiB and `vendor_boot_a` = 100 MiB. The variable name refers to the build's boot-image partition size; it does not, by itself, configure `vendor_boot` (the corresponding Android build variable is `BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE`). These old trees use a 2023 Android 12 build fingerprint, so a different firmware/layout is possible. Treat this as a mismatch to trace to the exact firmware/tree revision, not proof that the 100 MiB value was intended for `vendor_boot` or that every RMX3511 firmware has a 64 MiB boot partition.
3. **Super size mismatch also needs firmware/version verification.** Both declare `BOARD_SUPER_PARTITION_SIZE := 9126805504` (9,126,805,504 bytes), while the inspected firmware XML declares 8000 MiB (8,388,608,000 bytes). The generated dynamic-partition size is also hardcoded to 9,122,611,200 bytes, larger than this XML's entire super partition. Since the tree is from 2023 and the inspected firmware is from 2024, verify the tree's target firmware/partition map before calling this a universal device defect; for the inspected firmware, these values do not match.
4. **Filesystem assumptions are stale/inconsistent.** Both trees set `BOARD_SYSTEMIMAGE_PARTITION_TYPE := ext4` and `BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4`. The newer tree's fstab has EROFS entries for `system`, `system_ext`, `vendor`, `product`, and `vendor_dlkm`, consistent with the extracted first-stage fstab and Android 13 AVB package descriptors for system/product. The older tree's logical partition entries are ext4-only. The recovery fstab needs to support the filesystems actually present; image-build variables and mount fstab entries must be audited separately.
5. **The newer tree duplicates `system` in the dynamic partition list:** `system system system_ext vendor product vendor_dlkm`. The older tree's list is `system system_ext vendor product vendor_dlkm`. Do not copy the duplicate.
6. **Data encryption is under-specified in both TWRP fstabs.** Their `/data` entry specifies F2FS but omits the stock recovery fstab's file-encryption and metadata key-directory options. Even if TWRP boots and mounts F2FS, successful decryption of user data is not established. Keep data decryption as a separate compatibility test; do not promise it from these files.
7. **The generated trees are based on older device properties.** Their product makefiles identify an Android 12-era build description/fingerprint from 2023, while the installed system reports Android 13 build `R.202408010030`. The current package itself also reports Android 12 vendor and Android 13 system AVB properties. This is a compatibility point to verify, not sufficient proof by itself that the device tree cannot be used.

### Immediate engineering conclusion

Neither public tree is a trustworthy drop-in build configuration. The useful parts are the device identity, kernel command line, Unisoc platform name, and a starting inventory of physical partition names. Before choosing build flags, inspect the actual TWRP/Android build source for its header-v4 and vendor_boot support, then derive a corrected BoardConfig from the observed firmware. Keep the stock kernel and DTB as prebuilts initially; do not add kernel rebuilding to the first recovery milestone. The first milestone should be a reproducibly built image with correct packaging and a verified non-destructive boot method, not userdata decryption or flashing.
