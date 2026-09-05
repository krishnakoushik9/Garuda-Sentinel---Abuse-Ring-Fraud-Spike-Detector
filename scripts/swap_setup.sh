#!/usr/bin/env bash

# Garuda Sentinel - Aggressive Swap Setup & Selective RAM Protection Configuration Script
# This script configures the system sysctl, cgroups, and user limits.
# MUST BE RUN WITH SUDO.

set -e

# Colors for professional output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}      Garuda Sentinel - Aggressive Swap & RAM Protection Setup        ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# Check for root/sudo
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Error: This script must be run as root or with sudo privileges.${NC}"
  exit 1
fi

# 1. Update sysctl.conf for swappiness and cache pressure persistence
echo -e "\n${BLUE}[1/4] Tuning sysctl parameters (/etc/sysctl.conf)...${NC}"

# Remove existing configurations if any to prevent duplicates
sed -i '/vm.swappiness/d' /etc/sysctl.conf
sed -i '/vm.vfs_cache_pressure/d' /etc/sysctl.conf

# Add aggressive swap configurations
echo "vm.swappiness=100" >> /etc/sysctl.conf
echo "vm.vfs_cache_pressure=500" >> /etc/sysctl.conf

echo -e "${GREEN}✓ Added vm.swappiness=100 to /etc/sysctl.conf${NC}"
echo -e "${GREEN}✓ Added vm.vfs_cache_pressure=500 to /etc/sysctl.conf${NC}"

# Load settings immediately
echo -e "Loading sysctl parameters at runtime..."
sysctl -p

# 2. Configure user limits for mlock privilege without root
echo -e "\n${BLUE}[2/4] Configuring memory locking limits (/etc/security/limits.conf)...${NC}"

# Remove existing memlock configurations to prevent duplicates
sed -i '/memlock/d' /etc/security/limits.conf

# Add unlimited memlock for all users
echo "* soft memlock unlimited" >> /etc/security/limits.conf
echo "* hard memlock unlimited" >> /etc/security/limits.conf

echo -e "${GREEN}✓ Added unlimited soft/hard memlock permissions for all users.${NC}"
echo -e "${YELLOW}Note: You may need to log out and log back in (or restart services) for memlock limits to take effect.${NC}"

# 3. Configure cgroups v2 memory controller permissions
echo -e "\n${BLUE}[3/4] Tuning cgroups v2 controller capability...${NC}"
if [ -f "/sys/fs/cgroup/cgroup.controllers" ]; then
    # Ensure memory controller is enabled in cgroups v2
    if grep -q "memory" /sys/fs/cgroup/cgroup.controllers; then
        echo -e "${GREEN}✓ cgroups v2 memory controller is present and supported.${NC}"
        # Enable it in subtree_control if not already
        if ! grep -q "memory" /sys/fs/cgroup/cgroup.subtree_control; then
            echo "+memory" > /sys/fs/cgroup/cgroup.subtree_control 2>/dev/null || echo -e "${YELLOW}Warning: Could not enable memory controller in root cgroup subtree_control.${NC}"
        fi
    else
        echo -e "${YELLOW}Warning: memory controller not found in /sys/fs/cgroup/cgroup.controllers.${NC}"
    fi
else
    echo -e "${YELLOW}System is not running cgroups v2 (no /sys/fs/cgroup/cgroup.controllers found). Fallback to mlockall will be used.${NC}"
fi

# 4. Verify system swap availability
echo -e "\n${BLUE}[4/4] Verifying swap memory pool...${NC}"
SWAP_TOTAL=$(free -m | awk '/Swap/ {print $2}')
if [ -z "$SWAP_TOTAL" ] || [ "$SWAP_TOTAL" -eq 0 ]; then
    echo -e "${RED}Error: No swap space detected. Please set up a swap partition or file first!${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Detected $SWAP_TOTAL MB of available swap memory.${NC}"
fi

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${GREEN}System successfully configured!${NC}"
echo -e "${BLUE}To apply memlock limits completely, please restart the API backend process.${NC}"
echo -e "${BLUE}======================================================================${NC}"
