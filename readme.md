# Odin LLDB script

Python script to visualize Odin slices, maps, strings, etc. in LLDB.

Based on the work of [harold-b](https://gist.github.com/harold-b/ef16a5c3ebcceccfc2bc7a5c5dd0058d) and [laytan](https://gist.github.com/laytan/a94c323a84cef7bcfbdf6d21987fd5a9).

## Installation

Refer to https://gist.github.com/laytan/a94c323a84cef7bcfbdf6d21987fd5a9?permalink_comment_id=5036057#gistcomment-5036057

## Development

### Running tests

To run the tests locally:

```bash
./test.py
```

### LLDB Python Module

To point the Python LSP extension to the LLDB module.

1. Get the path to the LLDB Python module:

```bash
echo "$(lldb --python-path)/lldb"
```

2. Add the path to your VSCode settings:
```jsonc
{
	"python.analysis.extraPaths": [
		"/usr/lib/llvm-17/lib/python3.12/site-packages/lldb"
	],
}
```

### Resources

- https://lldb.llvm.org/use/variable.html
- https://melatonin.dev/blog/how-to-create-lldb-type-summaries-and-synthetic-children-for-your-custom-types
