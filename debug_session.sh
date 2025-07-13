#!/bin/bash

./build.sh

lldb main.bin \
     --no-lldbinit \
     -o "command script import odin.py" \
     -o "b breakpoint" \
     -o "r" \
     -o "up"