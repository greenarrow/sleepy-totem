#!/bin/bash

echo Installing sleepy-totem to $HOME/.local/share/totem/plugins
mkdir -p $HOME/.local/share/totem/plugins
cp -R sleepy-totem $HOME/.local/share/totem/plugins
echo Done

