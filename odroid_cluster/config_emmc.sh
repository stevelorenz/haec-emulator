#! /bin/bash
#
#

EMMC_DEV="/dev/sdc"
HOSTNAME="$1"
MOUNT_DIR="/run/media/rootfs"

echo "Hostname: $HOSTNAME"

sudo umount "$EMMC_DEV1"
sudo umount "$EMMC_DEV2"

lsblk
df

echo "Start copying image to $EMMC_DEV"
sudo dd if="$HOME/image/odroid/ubuntu-18.04-4.14-mate-odroid-xu4-20180501-maxinet.img" of="$EMMC_DEV"
sync
sync
sync

echo "Run configs"
sudo mkdir -p "$MOUNT_DIR"
sudo mount "$EMMC_DEV2" "$MOUNT_DIR"

sudo sed -i "s/odroid/$HOSTNAME/" "$MOUNT_DIR/etc/hostname"
sudo sed -i "s/odroid/$HOSTNAME/" "$MOUNT_DIR/etc/hosts"
