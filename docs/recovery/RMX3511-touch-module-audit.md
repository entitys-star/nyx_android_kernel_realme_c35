# RMX3511 touch-driver audit

Date: 2026-10-17

## Findings from the supplied stock partition images

The mounted `vendor_dlkm_a.img` listing contains these relevant modules:

- `focaltech_ft8756_spi_ts.ko`
- `sprd-focaltech.ko`
- `chipone-tddi.ko`
- `ilitek.ko`
- `sprd-nt36xxx.ko`
- `himax_mmi.ko`

This confirms that the stock vendor_dlkm partition ships a FocalTech FT8756 SPI touchscreen module. It does **not** yet prove that this is the active panel overlay on the particular handset, or that the module can be loaded by TWRP without additional dependencies.

The inspected `vendor_a.img` firmware directory did not contain a file named for FT8756/FocalTech. It did contain files for other touch-controller families, including FTS8006SAA, Himax, ICNL9911C and Novatek, plus `Nico_Huaqin_CID3501_D00_C81_20220429.bin` and `Nico_Huaqin_CID3502_D00_C01_20220429.bin`. Do not assume those two Nico/Huaqin blobs are FT8756 firmware without validating their format/content. A name search in `product_a.img` returned no touch-firmware candidates.

## Driver-source cross-check

The public Realme C31/C35/Narzo 50A Prime Android R kernel source contains a FocalTech SPI driver at:

- [focaltech_ft8756_spi source directory](https://github.com/realme-kernel-opensource/realme_C31_C35_narzo50A-Prime-AndroidR-kernel-source/tree/79c7c8b238a20393a78ee5f1110991bd4280e143/drivers/kernel_modules/input/touchscreen/focaltech_ft8756_spi)
- [focaltech_core.c](https://github.com/realme-kernel-opensource/realme_C31_C35_narzo50A-Prime-AndroidR-kernel-source/blob/79c7c8b238a20393a78ee5f1110991bd4280e143/drivers/kernel_modules/input/touchscreen/focaltech_ft8756_spi/focaltech_core.c)
- [focaltech_config.h](https://github.com/realme-kernel-opensource/realme_C31_C35_narzo50A-Prime-AndroidR-kernel-source/blob/79c7c8b238a20393a78ee5f1110991bd4280e143/drivers/kernel_modules/input/touchscreen/focaltech_ft8756_spi/focaltech_config.h)
- [focaltech_flash.c](https://github.com/realme-kernel-opensource/realme_C31_C35_narzo50A-Prime-AndroidR-kernel-source/blob/79c7c8b238a20393a78ee5f1110991bd4280e143/drivers/kernel_modules/input/touchscreen/focaltech_ft8756_spi/focaltech_flash.c)

That source identifies the SPI driver name as `fts_ts` and the device-tree compatible as `focaltech,fts`. Its public configuration has firmware-request loading disabled and refers to an embedded include named `include/firmware/FT8756_V30_D00_20201225_app.i`; that firmware include was not present in the listed public source tree. This is useful background only: it is an Android R source tree, not proof that its driver binary or firmware matches the RMX3511T2_13.F.73 stock module.

## Required checks before declaring TWRP touch support

1. Read the exact stock module metadata and dependency records: `modinfo focaltech_ft8756_spi_ts.ko`, `modules.dep`, `modules.load`, and any recovery-specific module load list from the same `vendor_dlkm_a.img`.
2. Check whether the stock module has an acceptable `vermagic` for the stock kernel extracted from `boot.img`. Do not rebuild this driver from a different kernel tree and expect ABI compatibility.
3. Inspect the stock DTB and all 21 DTBO overlays for an enabled SPI node matching `compatible = "focaltech,fts"`, its `status`, GPIOs, regulators, SPI bus and display coordinates. The active overlay is still unconfirmed.
4. Determine whether the stock module embeds its firmware or requests an external firmware file. Do not substitute FTS8006SAA or other vendor blobs by filename similarity.
5. If the module is required in recovery, package the exact stock module and its dependency modules into the recovery environment and explicitly arrange loading after the relevant buses/GPIO providers are available. Verify input events in a boot test before treating touch as working.

## Current conclusion

**FT8756 driver availability is confirmed; working TWRP touch is not.** Keep the initial recovery build focused on preserving the stock kernel/DTB and getting a bootable recovery. Do not claim touch support until the active DTBO, module load order and actual recovery input events are verified.


## Additional inspection of the extracted stock vendor_boot ramdisk

The matching `vendor_boot.img` and `dtbo.img` were available in the Library and were inspected locally.

- The stock recovery ramdisk itself already contains `/lib/modules/focaltech_ft8756_spi_ts.ko`.
- Its `modinfo` reports `vermagic: 5.4.254-android12-9-g0b4c88190d9d-ab1584 SMP preempt mod_unload modversions aarch64`, no hard module dependencies, and aliases for `focaltech,fts`.
- `/lib/modules/modules.load.recovery` includes `focaltech_ft8756_spi_ts.ko` at line 123 and `sprd-focaltech.ko` at line 153.
- `modules.alias` maps `oppo,touchscreen` to `sprd_focaltech`; it maps `focaltech,fts` to `focaltech_ft8756_spi_ts`.
- `modules.dep` lists `sprd-focaltech.ko` as depending on `sprd-nt36xxx.ko`, `sprd-drm.ko`, `lcd_bias_adjust.ko`, `apsys-dvfs.ko`, `sprd-gsp.ko`, `unisoc-iommu.ko`, `trusty-ipc.ko`, and `hq_hardware_info.ko`. The FT8756-specific module has no listed hard dependencies.

The DTBO image has 21 entries. The base DTB from `vendor_boot.img` contains the enabled SPI controller at `/soc/ap-apb/spi@20120000`, with other AP SPI controllers disabled. DTBO entries contain a `/fragment@7/__overlay__/touchscreen@0` node with `compatible = "oppo,touchscreen"`, SPI max frequency `0x927c00` (9.6 MHz), touch IRQ/reset GPIO references, and 720×1600 coordinate properties. Entries 14–20 additionally include `focaltech,max-touch-number = 10` and `focaltech,display-coords = <0 0 720 1600>`. These nodes match the `sprd-focaltech` alias, **not** the `focaltech,fts` alias of the FT8756-specific module.

The DTBO contains multiple LCD candidates, including `lcd_ft8006saa_inx_mipi_hd`, and the vendor firmware partition contains FTS8006SAA firmware files. This makes the generic `sprd-focaltech` driver a strong candidate for the actual overlay path, but the active overlay/panel still cannot be proven from the table alone. Do not hard-code FT8756 as the handset's active controller yet.

This improves the recovery plan: retain the stock recovery ramdisk module set and its `modules.load.recovery` ordering rather than inventing a new module load list. Verify the merged live device tree or recovery input events before pruning any alternative drivers.
