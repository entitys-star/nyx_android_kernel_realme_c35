# Recovery preparation tools

## Extract the DTB payload

Run from the root of this repository with the matching stock `vendor_boot.img`:

```sh
python3 tools/extract_vendor_boot_dtb.py /path/to/vendor_boot.img
```

The script writes `device/realme/ums9230_nico/prebuilt/dtb.img`. It preserves the full DTB payload, including an Android DT table if present, rather than extracting only the first FDT.

For the image currently examined, expected values are:
- vendor_boot v4, page size 4096;
- DTB payload offset 24,698,880;
- DTB payload size 163,976 bytes;
- payload starts with Android DT table magic `d7b7ab1e`, with one FDT entry.

The rest of the vendor ramdisk still needs to be staged into `device/realme/ums9230_nico/recovery/root` using the audited Unisoc generator or an equivalent reviewed extraction process. Do not assume the tree builds until those stock runtime files and the correct TWRP source overlay are present.
