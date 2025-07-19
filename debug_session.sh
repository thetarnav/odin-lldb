#!/bin/bash

./build.sh

lldb main.bin \
     --no-lldbinit \
     -o "command script import odin.py" \
     -o "command script import print_children.py" \
     -o "b breakpoint" \
     -o "r" \
     -o "up"