LOCAL_PATH := device/realme/ums9230_nico

PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_SHIPPING_API_LEVEL := 30 # ro.product.first_api_level in stock ramdisk

# The generated/extracted stock vendor ramdisk must be staged here before build.
# This copies its recovery-only vendor runtime without including kernel sources.
SPRD_VENDOR_RAMDISK_FILES := $(call find-copy-subdir-files,*,$(LOCAL_PATH)/recovery/root,vendor_ramdisk)
PRODUCT_COPY_FILES += $(SPRD_VENDOR_RAMDISK_FILES)
SPRD_VENDOR_RAMDISK_FILES :=

PRODUCT_PACKAGES += \
    check_f2fs \
    dump.erofs \
    f2fs_io \
    fsck.erofs \
    sg_write_buffer \
    checkpoint_gc \
    snapuserd \
    android.hardware.fastboot@1.0-impl-mock \
    android.hardware.fastboot@1.0-impl-mock.recovery \
    fastbootd

PRODUCT_HOST_PACKAGES += mkfs.erofs
