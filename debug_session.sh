#!/bin/bash

./build.sh

lldb main.bin \
     -o "command script import odin.py" \
     -o "b breakpoint" \
     -o "r" \
     -o "up"