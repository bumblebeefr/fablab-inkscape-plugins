#!/bin/bash
Xvfb :8 -screen 0 1024x768x8 > /dev/null 2>&1 &
XVFB_PID=$!
export DISPLAY=":8"
inkscape $@ > /dev/null 2>&1
kill $XVFB_PID
