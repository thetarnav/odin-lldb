#!/bin/bash

lldb -o "command script import odin.py" \
     -o "b main.bin\`main" \
     -o "r" \
     -o "n" \
     -o "n" \
     -o "n" \
     -o "s" \
     -o "n" \
     -o "n" \
     -o "n" \
     -o "n" \
     -o "n" \
     -o "n" \
     -o "p foo_bar_union" \
     -o "p foo_bar_union_no_nil" \
     -o "p foo_bar_union_shared_nil" \
     -o "frame variable" \
     -o "type lookup Foo_Bar_Union" \
     -o "type lookup Foo_Bar_Union_No_Nill" \
     -o "q" \
     main.bin
