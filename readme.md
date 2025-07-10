# LLDB Python Module

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
