#!/bin/bash
git pull
mkdir -p ~/.config/inkscape/extensions/
ln -f -s $(pwd)/fablab* ~/.config/inkscape/extensions/