#!/bin/bash
git pull
mkdir -p ~/.config/inkscape/extensions/
mkdir -p ~/.config/inkscape/palettes/
ln -f -s $(pwd)/fablab* ~/.config/inkscape/extensions/
ln -f -s $(pwd)/palettes/* ~/.config/inkscape/palettes/
