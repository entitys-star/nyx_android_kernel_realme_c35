# RMX3511 stock vendor_boot extraction results

Firmware: `RMX3511T2_13.F.73`

The matching `vendor_boot.img` was recovered from the conversation Library and inspected locally. Its SHA-256 is:

`17e5c60be1414e56fabfaf50887aa1e2dc910e8dc6516ad2182fce182762c4b1`

Verified fields:

- Image size: 104,857,600 bytes (100 MiB)
- Header version: 4; header size: 2,128; page size: 4,096
- Vendor ramdisk: offset 4,096; compressed size 24,694,046 bytes
- Vendor ramdisk SHA-256: `814d35b6160aa67ba2bc2ae824d6f74cb8fd34483b5b9fc42d6b7d406b5c7633`
- DTB payload: offset 24,698,880; size 163,976 bytes
- DTB SHA-256: `39e76810dd1eb748b2459c9815e24b7d2ccc2378fb5abc53375e8efb455025ae`
- Vendor ramdisk table: one 108-byte platform fragment, offset zero
- Bootconfig size: zero
- Vendor command line: `console=ttyS1,115200n8 buildvariant=user`

The legacy-LZ4 stream decoded to a 54,150,400-byte newc CPIO archive. SHA-256:

`2ffa23a01d5b64d47c18ddc506e0d2505349e9881e9672a76468064324e20f81`

The extractor was tested against this image and consumed the complete compressed payload without trailing bytes. The extracted archive contains the stock recovery binary, recovery fstab, first-stage fstab, recovery init fragments, ueventd rules, and Unisoc kernel modules.

## Reproduce locally

From the repository root, with Python 3 and the Python `lz4` package installed:

```sh
python3 tools/audit_vendor_boot.py /path/to/vendor_boot.img -o /tmp/rmx3511-vendor-boot
python3 tools/extract_vendor_boot_ramdisk.py /path/to/vendor_boot.img -o /tmp/rmx3511-vendor-boot/vendor_ramdisk.cpio
mkdir -p /tmp/rmx3511-stock-root
cd /tmp/rmx3511-stock-root
cpio -idm --quiet --no-absolute-filenames < /tmp/rmx3511-vendor-boot/vendor_ramdisk.cpio
```

The ramdisk extraction helper is for the RMX3511 image's single legacy-LZ4 platform fragment; it is not a general-purpose multi-fragment vendor_boot unpacker.

## Still unresolved

- No TWRP source checkout/build environment is present in the current workspace, so no recovery image has been built.
- The exact active panel/touch overlay is not identified from the DTBO table alone.
- The exact module `focaltech_ft8756_spi_ts.ko` is present in the supplied `vendor_dlkm_a.img` listing. No FT8756-named standalone firmware file was found by filename/content search in `vendor_a.img` or `product_a.img`; the module may embed firmware, but this has not been confirmed. See [RMX3511 touch-module audit](RMX3511-touch-module-audit.md). The active DTBO and recovery module-loading path remain unverified.
- TWRP fstab/decryption, retained stock SELinux policy handling, AVB/rollback behavior, and non-destructive boot testing remain unverified.

Do not flash an image based only on these extraction results.
