$(call inherit-product, $(SRC_TARGET_DIR)/product/aosp_base.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product-if-exists, $(SRC_TARGET_DIR)/product/gsi_keys.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/full_base_telephony.mk)
$(call inherit-product-if-exists, vendor/twrp/config/common.mk)
$(call inherit-product, device/realme/ums9230_nico/device.mk)

PRODUCT_NAME := twrp_ums9230_nico
PRODUCT_DEVICE := ums9230_nico
PRODUCT_BRAND := realme
PRODUCT_MODEL := RMX3511
PRODUCT_MANUFACTURER := realme
PRODUCT_RELEASE_NAME := RMX3511
PRODUCT_BUILD_PROP_OVERRIDES += PRIVATE_BUILD_DESC="RE87BAL1-user 13 TP1A.220905.001 RMX3511T2_13.F.73 release-keys"
