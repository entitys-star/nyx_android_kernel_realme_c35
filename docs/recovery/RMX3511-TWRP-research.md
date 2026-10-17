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
