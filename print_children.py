import lldb

def print_children(
    debugger: lldb.SBDebugger,
	command:  str,
	result:   lldb.SBCommandReturnObject,
	_dict:    dict,
) -> None:

    var_name = command.strip()
    if not var_name:
        result.AppendMessage("Usage: print_children <variable_name>")
        return

    frame = debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
    variable = frame.FindVariable(var_name)
    
    if not variable.IsValid():
        result.AppendMessage(f"Variable '{var_name}' not found")
        return
    
    num_children = variable.GetNumChildren()
    if num_children == 0:
        result.AppendMessage("  No children")
        return

    for i, child in enumerate(variable.children):
        name  = child.GetName()
        value = child.GetSummary() or child.GetValue()
        result.AppendMessage(f"[{i}] {name} = {value}")

def __lldb_init_module(debugger, internal_dict):
    debugger.HandleCommand('command script add -f print_children.print_children print_children')
    print("Added 'print_children' command")
