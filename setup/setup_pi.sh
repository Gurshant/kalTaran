#!/bin/bash
set -e  # exit immediately if a command fails

echo "=== Updating system packages ==="
sudo apt update -y
sudo apt install -y wmctrl git openssh-client

echo "=== Configuring Git ==="
git config --global user.name "Gurshant"
git config --global user.email "gurshant53@gmail.com"

echo "=== Generating SSH key ==="
if [ ! -f ~/.ssh/id_ed25519 ]; then
    ssh-keygen -t ed25519 -C "gurshant53@gmail.com" -f ~/.ssh/id_ed25519 -N ""
else
    echo "SSH key already exists, skipping..."
fi

echo "=== Adding SSH key to agent ==="
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

USB_PATH="/media/$(whoami)/BCC6-B15E"

echo "=== Copying SSH public key to USB (if mounted) ==="
if [ -d "$USB_PATH" ]; then
    cp ~/.ssh/id_ed25519.pub "$USB_PATH/"
    echo "Public key copied to $USB_PATH/"
else
    echo "USB drive not found at $USB_PATH, please insert and mount it."
fi

echo "=== Setup complete! ==="

