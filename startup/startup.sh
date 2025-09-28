#!/bin/bash

sleep 5

lxterminal -e wmctrl -a kalTaran &


# Pull latest code
cd ~/Desktop/kalTaran || exit
git pull

python3 ~/Desktop/kalTaran/StepRoomController.py 

