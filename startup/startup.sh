#!/bin/bash

sleep 5

numlockx on 

lxterminal -e wmctrl -a StepRoom &

python3 ~/Desktop/kaltaran/StepRoomController.py 

