#!/bin/bash
set -e  # exit if anything fails

echo "=== Moving to Desktop ==="
cd ~/Desktop

echo "=== Cloning repository ==="
if [ ! -d "kalTaran" ]; then
    git clone git@github.com:Gurshant/kalTaran.git
else
    echo "Repository already exists, pulling latest changes..."
    cd kalTaran
    git pull
    cd ..
fi

echo "=== Setting up autostart ==="
mkdir -p ~/.config/autostart

cp ~/Desktop/kalTaran/config_default.py ~/Desktop/kalTaran/config_local.py 

cp ~/Desktop/kalTaran/startup/startup.desktop ~/.config/autostart/

echo "=== Done! The app will now autostart on login. ==="

