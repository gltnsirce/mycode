# ============================================================
# RHEL 9 Enterprise Automated Installation
#
# Target:
#   - Dell
#   - HPE
#   - Cisco UCS
#
# Installation:
#   PXE -> HTTP -> Kickstart -> Anaconda
#
# Management:
#   Ansible
#
# ============================================================


# ============================================================
# 1. Installation source
# ============================================================

url --url="http://192.168.2.10/rhel9"


# ============================================================
# 2. Language / Keyboard / Timezone
# ============================================================

lang en_US.UTF-8
keyboard us

timezone Asia/Shanghai --utc


# ============================================================
# 3. Network
#
# DHCP is used during installation.
# The final IP configuration can later be managed by Ansible.
# ============================================================

network --bootproto=dhcp --device=link --activate


# ============================================================
# 4. Authentication
#
# Do NOT put production passwords in this file.
#
# Example encrypted password only.
# Replace with your own SHA-512 crypt password.
# ============================================================

rootpw --iscrypted $6$REPLACE_WITH_YOUR_HASH


# ============================================================
# 5. Initial user for Ansible management
# ============================================================

user --name=ansible \
     --groups=wheel \
     --shell=/bin/bash \
     --password=$6$REPLACE_WITH_YOUR_HASH \
     --iscrypted


# ============================================================
# 6. SSH
# ============================================================

services --enabled="sshd"


# ============================================================
# 7. SELinux
# ============================================================

selinux --enforcing


# ============================================================
# 8. Firewall
# ============================================================

firewall --enabled --service=ssh


# ============================================================
# 9. Bootloader
# ============================================================

bootloader --location=mbr


# ============================================================
# 10. Storage
#
# IMPORTANT:
#
# Do not assume:
#
#     /dev/sda
#
# because Dell / HPE / UCS may enumerate disks differently.
#
# autopart lets Anaconda select the installation disk automatically.
#
# For production environments with multiple SAN/NVMe/local disks,
# replace this section with WWID/by-id based selection.
# ============================================================

zerombr

clearpart --all --initlabel

autopart --type=lvm


# ============================================================
# 11. Package selection
# ============================================================

%packages --ignoremissing

@^minimal-environment

openssh-server
openssh-clients

sudo

chrony

vim-enhanced
bash-completion

curl
wget
rsync

tar
gzip
bzip2
unzip

pciutils
usbutils

lsof
psmisc

bind-utils
iproute
iputils

net-tools

ethtool

dmidecode

lsscsi

util-linux

smartmontools

python3

python3-pip

dnf-utils

rsyslog

logrotate

tuned

vim

git

%end


# ============================================================
# 12. %pre
#
# Runs inside the Anaconda installer environment.
#
# Purpose:
#   Detect hardware before installation.
#
# We do NOT attempt to configure the final Linux system here.
# We only collect hardware information.
# ============================================================

%pre --log=/tmp/ks-pre.log

echo "============================================" > /tmp/hardware-info
echo "Hardware detection started" >> /tmp/hardware-info
date >> /tmp/hardware-info
echo "============================================" >> /tmp/hardware-info


# ------------------------------------------------------------
# Vendor
# ------------------------------------------------------------

if [ -f /sys/class/dmi/id/sys_vendor ]; then
    SYS_VENDOR=$(cat /sys/class/dmi/id/sys_vendor)
else
    SYS_VENDOR="UNKNOWN"
fi

echo "SYS_VENDOR=$SYS_VENDOR" >> /tmp/hardware-info


# ------------------------------------------------------------
# Product
# ------------------------------------------------------------

if [ -f /sys/class/dmi/id/product_name ]; then
    PRODUCT_NAME=$(cat /sys/class/dmi/id/product_name)
else
    PRODUCT_NAME="UNKNOWN"
fi

echo "PRODUCT_NAME=$PRODUCT_NAME" >> /tmp/hardware-info


# ------------------------------------------------------------
# Serial number
# ------------------------------------------------------------

if [ -f /sys/class/dmi/id/product_serial ]; then
    SERIAL=$(cat /sys/class/dmi/id/product_serial)
else
    SERIAL="UNKNOWN"
fi

echo "SERIAL=$SERIAL" >> /tmp/hardware-info


# ------------------------------------------------------------
# BIOS
# ------------------------------------------------------------

if [ -f /sys/class/dmi/id/bios_vendor ]; then
    BIOS_VENDOR=$(cat /sys/class/dmi/id/bios_vendor)
else
    BIOS_VENDOR="UNKNOWN"
fi

echo "BIOS_VENDOR=$BIOS_VENDOR" >> /tmp/hardware-info


# ------------------------------------------------------------
# Detect manufacturer
# ------------------------------------------------------------

case "$SYS_VENDOR" in

    *Dell*|*DELL*)
        PLATFORM="DELL"
        ;;

    *HPE*|*HP*|*Hewlett*)
        PLATFORM="HPE"
        ;;

    *Cisco*)
        PLATFORM="CISCO_UCS"
        ;;

    *)
        PLATFORM="UNKNOWN"
        ;;

esac


echo "PLATFORM=$PLATFORM" >> /tmp/hardware-info


# ------------------------------------------------------------
# CPU
# ------------------------------------------------------------

if command -v lscpu >/dev/null 2>&1; then
    lscpu >> /tmp/hardware-info
fi


# ------------------------------------------------------------
# PCI devices
# ------------------------------------------------------------

echo "" >> /tmp/hardware-info
echo "========== PCI DEVICES ==========" >> /tmp/hardware-info

if command -v lspci >/dev/null 2>&1; then
    lspci >> /tmp/hardware-info
fi


# ------------------------------------------------------------
# Storage
# ------------------------------------------------------------

echo "" >> /tmp/hardware-info
echo "========== BLOCK DEVICES ==========" >> /tmp/hardware-info

if command -v lsblk >/dev/null 2>&1; then
    lsblk -e 7 -o NAME,KNAME,TYPE,SIZE,MODEL,SERIAL,WWN >> /tmp/hardware-info
fi


# ------------------------------------------------------------
# Network
# ------------------------------------------------------------

echo "" >> /tmp/hardware-info
echo "========== NETWORK ==========" >> /tmp/hardware-info

ip link >> /tmp/hardware-info


# ------------------------------------------------------------
# Save platform information
# ------------------------------------------------------------

cat > /tmp/platform-info <<EOF
PLATFORM=$PLATFORM
SYS_VENDOR=$SYS_VENDOR
PRODUCT_NAME=$PRODUCT_NAME
SERIAL=$SERIAL
BIOS_VENDOR=$BIOS_VENDOR
EOF


echo ""
echo "Detected platform:"
cat /tmp/platform-info

echo ""
echo "Hardware information:"
cat /tmp/hardware-info

%end


# ============================================================
# 13. Services
# ============================================================

services --enabled="sshd,chronyd,rsyslog"


# ============================================================
# 14. First boot
# ============================================================

firstboot --disable


# ============================================================
# 15. Reboot after installation
# ============================================================

reboot


# ============================================================
# 16. %post
#
# Runs after RHEL has been installed.
#
# This is where we prepare the OS for Ansible management.
# ============================================================

%post --log=/root/ks-post.log

set -x


# ============================================================
# A. Record installation information
# ============================================================

mkdir -p /etc/provisioning

cat > /etc/provisioning/installation-info <<EOF
InstallationDate=$(date)
Kickstart=PXE
Provisioning=Kickstart
Management=Ansible
EOF


# ============================================================
# B. Detect vendor again
#
# This time we are running inside the installed RHEL system.
# ============================================================

SYS_VENDOR=$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null || echo UNKNOWN)
PRODUCT_NAME=$(cat /sys/class/dmi/id/product_name 2>/dev/null || echo UNKNOWN)
SERIAL=$(cat /sys/class/dmi/id/product_serial 2>/dev/null || echo UNKNOWN)


case "$SYS_VENDOR" in

    *Dell*|*DELL*)
        PLATFORM="DELL"
        ;;

    *HPE*|*HP*|*Hewlett*)
        PLATFORM="HPE"
        ;;

    *Cisco*)
        PLATFORM="CISCO_UCS"
        ;;

    *)
        PLATFORM="UNKNOWN"
        ;;

esac


cat > /etc/provisioning/hardware.conf <<EOF
PLATFORM=$PLATFORM
SYS_VENDOR=$SYS_VENDOR
PRODUCT_NAME=$PRODUCT_NAME
SERIAL=$SERIAL
EOF


# ============================================================
# C. Configure sudo for Ansible
# ============================================================

cat > /etc/sudoers.d/ansible <<EOF
ansible ALL=(ALL) NOPASSWD: ALL
EOF

chmod 440 /etc/sudoers.d/ansible


# ============================================================
# D. SSH configuration
# ============================================================

sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' \
    /etc/ssh/sshd_config

sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' \
    /etc/ssh/sshd_config


# ============================================================
# E. Enable SSH
# ============================================================

systemctl enable sshd


# ============================================================
# F. Enable chrony
# ============================================================

systemctl enable chronyd


# ============================================================
# G. Configure chrony
#
# Replace these with your enterprise NTP servers.
# ============================================================

cat > /etc/chrony.conf <<EOF
server 192.168.2.10 iburst
server 192.168.2.11 iburst

driftfile /var/lib/chrony/drift

makestep 1.0 3

rtcsync

keyfile /etc/chrony.keys

leapsectz right/UTC

logdir /var/log/chrony
EOF


# ============================================================
# H. Configure hostname behavior
#
# DHCP may initially provide hostname.
# Ansible should normally manage the final hostname.
# ============================================================

hostnamectl set-hostname localhost


# ============================================================
# I. Enable tuned
# ============================================================

systemctl enable tuned


# ============================================================
# J. Create provisioning information
# ============================================================

mkdir -p /etc/provisioning

cat > /etc/provisioning/provisioning.conf <<EOF
provisioned_by=kickstart
configuration_management=ansible
platform=$PLATFORM
vendor=$SYS_VENDOR
product=$PRODUCT_NAME
serial=$SERIAL
EOF


# ============================================================
# K. Validate sudo configuration
# ============================================================

chmod 600 /etc/ssh/sshd_config

chmod 440 /etc/sudoers.d/ansible


# ============================================================
# L. Reload SSH configuration
# ============================================================

systemctl enable sshd


# ============================================================
# M. Mark machine as Kickstart provisioned
# ============================================================

touch /etc/provisioning/kickstart-complete


echo "Kickstart post installation completed."


%end
