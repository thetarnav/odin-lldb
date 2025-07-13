"""
Python script to visualize Odin slices, maps, strings, etc. in LLDB.

Based on harold-b's script: https://gist.github.com/harold-b/ef16a5c3ebcceccfc2bc7a5c5dd0058d
and laytan's script: https://gist.github.com/laytan/a94c323a84cef7bcfbdf6d21987fd5a9

Repository: https://github.com/thetarnav/odin-lldb
"""

import lldb
import math
import enum


class Odin_Type(enum.Enum):
    SLICE  = "slice"
    STRING = "string" 
    MAP    = "map"
    UNION  = "union"
    STRUCT = "struct"
    PROC   = "proc"
    OTHER  = "other"

def get_odin_type(t: lldb.SBType) -> Odin_Type:

    if t.name == "string":
        return Odin_Type.STRING
    
    if (t.name.startswith("[]") or t.name.startswith("[dynamic]")) and not t.name.endswith(']'):
        return Odin_Type.SLICE
    
    if t.name.startswith("map["):
        return Odin_Type.MAP
    
    if t.name.startswith("proc"):
        return Odin_Type.PROC
    
    if t.type == lldb.eTypeClassUnion:
        tag = t.GetFieldAtIndex(0)
        if tag and tag.IsValid() and tag.name == "tag":
            return Odin_Type.UNION
    
    if t.type == lldb.eTypeClassStruct:
        return Odin_Type.STRUCT
    
    return Odin_Type.OTHER

def is_type_slice  (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.SLICE
def is_type_string (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.STRING
def is_type_map    (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.MAP
def is_type_struct (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.STRUCT
def is_type_union  (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.UNION
def is_type_proc   (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.PROC
def is_type_pointer(t: lldb.SBType, _dict) -> bool: return t.is_pointer

def slice_summary(value: lldb.SBValue, _dict) -> str:
    value  = value.GetNonSyntheticValue()
    length = value.GetChildMemberWithName("len").unsigned
    data   = value.GetChildMemberWithName("data")

    pointee   = data.deref
    type_name = pointee.type.GetDisplayTypeName()

    return f"[{length}]{type_name}"

class SliceChildProvider:
    CHUNK_COUNT = 2000

    def __init__(self, val, dict):
        self.val = val
        self.update()

    def update(self):
        val = self.val

        self.len        = val.GetChildMemberWithName("len").unsigned
        self.data_val   = val.GetChildMemberWithName("data")
        assert self.data_val.type.is_pointer

        is_chunked       = self.len > SliceChildProvider.CHUNK_COUNT
        self.chunked_len = 0 if not is_chunked else math.ceil(self.len / SliceChildProvider.CHUNK_COUNT)

        return False

    def num_children(self):
        return self.chunked_len if self.chunked_len > 0 else self.len

    def get_child_at_index(self, index):
        length = self.num_children()
        assert index >= 0 and index < length

        first = self.data_val.deref

        if self.chunked_len > 0:
            chunk_size = SliceChildProvider.CHUNK_COUNT

            array_len = min(chunk_size, self.len - index * chunk_size)
            arr_type  = first.type.GetArrayType(array_len)
            offset    = index * first.size * chunk_size

            range_start = index * chunk_size

            return self.data_val.CreateChildAtOffset(f"[{range_start}..<{range_start+array_len}]", offset, arr_type)

        offset = index * first.size
        return self.data_val.CreateChildAtOffset(f"[{index}]", offset, first.type)

def string_summary(value: lldb.SBValue, _dict) -> str | None:
    pointer = value.GetChildMemberWithName("data").GetValueAsUnsigned(0)
    length = value.GetChildMemberWithName("len").GetValueAsSigned(0)
    if pointer == 0:
        return None
    if length == 0:
        return '""'
    error = lldb.SBError()
    string_data = value.process.ReadMemory(pointer, length, error)
    return '"{}"'.format(string_data.decode("utf-8"))

class MapChildProvider:

    def __init__(self, val, dict):
        self.val = val

    def num_children(self):
        return (self.val.GetChildMemberWithName("len").GetValueAsSigned() * 2) + 1

    def get_child_at_index(self, index):
        data = self.val.GetChildMemberWithName("data")
        tkey = data.GetChildMemberWithName("key").type
        tval = data.GetChildMemberWithName("value").type
        hash_field = data.GetChildMemberWithName("hash")
        key_cell   = data.GetChildMemberWithName("key_cell")
        value_cell = data.GetChildMemberWithName("value_cell")

        raw_data = data.GetValueAsUnsigned()
        key_ptr = raw_data & ~63
        cap_log2 = raw_data & 63
        cap = 0 if cap_log2 <= 0 else 1 << cap_log2

        key_cell_info = self.cell_info(tkey, key_cell)
        value_cell_info = self.cell_info(tval, value_cell)

        size_of_hash = hash_field.size
        assert size_of_hash == 8
    
        value_ptr = self.cell_index(key_ptr, key_cell_info, cap)
        hash_ptr =  self.cell_index(value_ptr, value_cell_info, cap)

        error = lldb.SBError()

        # Last one, the capacity.
        if index == self.num_children()-1:
            cap_data = lldb.SBData.CreateDataFromInt(cap)
            return self.val.CreateValueFromData("cap", cap_data, self.val.GetChildMemberWithName("len").type)

        wants_key = index % 2 == 0
        index = int(index / 2)

        key_index = 0
        for i in range(cap):
            TOMBSTONE_MASK = 1 << (size_of_hash*8 - 1)

            offset_hash = hash_ptr + i * size_of_hash

            hash_val = self.val.process.ReadUnsignedFromMemory(offset_hash, size_of_hash, error)
            if not error.success:
                print(error)
                continue
            elif hash_val == 0 or (hash_val & TOMBSTONE_MASK) != 0:
                continue

            offset_key   = self.cell_index(key_ptr, key_cell_info, i)
            offset_value = self.cell_index(value_ptr, value_cell_info, i)

            if index == key_index:
                if wants_key:
                    return self.val.CreateValueFromAddress(f"[{i}]", offset_key, tkey)
                else:
                    return self.val.CreateValueFromAddress(f"[{i}]", offset_value, tval)

            key_index += 1

        print("not found")

    def cell_info(self, typev, cell_type):
        elements_per_cell = 0

        if typev.size != cell_type.size:
            array_type = cell_type.children[0].type
            if array_type.size > 0 and typev.size > 0:
                elements_per_cell = array_type.size / typev.size

        if elements_per_cell == 0:
            elements_per_cell = 1

        return CellInfo(typev.size, cell_type.size, elements_per_cell)

    def cell_index(self, base, info, index):
        cell_index = 0
        data_index = 0
        if info.elements_per_cell == 1:
            return base + (index * info.size_of_cell)
        elif info.elements_per_cell == 2:
            cell_index = index >> 1;
            data_index = index & 1;
        elif info.elements_per_cell == 4:
            cell_index = index >> 2;
            data_index = index & 3;
        elif info.elements_per_cell == 8:
            cell_index = index >> 3;
            data_index = index & 7;
        elif info.elements_per_cell == 16:
            cell_index = index >> 4;
            data_index = index & 15;
        elif info.elements_per_cell == 32:
            cell_index = index >> 5;
            data_index = index & 31;
        else:
            cell_index = index / info.elements_per_cell;
            data_index = index % info.elements_per_cell;

        return base + (cell_index * info.size_of_cell) + (data_index * info.size_of_type);

class CellInfo:
    def __init__(self, size_of_type, size_of_cell, elements_per_cell):
        self.size_of_type = size_of_type
        self.size_of_cell = size_of_cell
        self.elements_per_cell = elements_per_cell


class UnionChildProvider:
    def __init__(self, val, dict):
        self.val = val

    def update(self):
        self.children      = self.val.children
        self.variant_index = self.children[0].unsigned
        self.is_no_nil     = detect_union_no_nil(self.val.type)
        
        return False

    def num_children(self):
        return len(self.children)-1

    def get_child_at_index(self, index):
        value = self.val

        variant_index = index+1
        variant       = self.children[variant_index]
        name          = variant.type.GetDisplayTypeName()
        
        if self.is_no_nil:
            selected = "*" if self.variant_index == index else ""
        else:
            selected = "*" if self.variant_index == variant_index else ""

        field_name = f"{selected}v{variant_index}({name})"
        c = value.CreateValueFromData(field_name, variant.data, variant.type)

        return c

def detect_union_no_nil(t: lldb.SBType) -> bool:
    """
    normal & #shared_nil union type:
        tag: u64
        v1:  T0
        v2:  T1
        ...
    #no_nil union type:
        tag: u64
        v0:  T0
        v1:  T1
        ...
    """
    tag_field = t.GetFieldAtIndex(0)
    first_variant = t.GetFieldAtIndex(1)

    return (
        tag_field is not None and tag_field.name == "tag" and
        first_variant is not None and first_variant.name == "v0"
    )

def union_summary(v: lldb.SBValue, _dict) -> str:
    if v.IsSynthetic():
        v = v.GetNonSyntheticValue()

    tag = v.GetChildAtIndex(0)
    assert(tag.name == "tag")
    
    tag_value = tag.unsigned
    variant_name = f"v{tag_value}"
    
    is_no_nil = detect_union_no_nil(v.type)
    
    if not is_no_nil and tag_value == 0:
        return "nil"
    
    variant: lldb.SBValue = v.GetChildMemberWithName(variant_name)
    if not variant.IsValid():
        return f"<invalid variant {variant_name}, tag={tag_value}, no_nil={is_no_nil}>"

    return f"{type_display(variant.type)}({value_summary(variant)})"

def struct_summary(v: lldb.SBValue, _dict) -> str:
    if v.IsSynthetic():
        v = v.GetNonSyntheticValue()
    
    output = "{"

    for i, field in enumerate(v.children):

        # Let LLDB handle the formatting using registered formatters
        output += value_summary(field)

        if i < len(v.children) - 1:
            output += ", "

    output += "}"
    return output

def type_display(t: lldb.SBType) -> str:
    name = t.name.replace("::", ".")
    if t.is_pointer:
        pointee: lldb.SBType = t.GetPointeeType()
        if pointee.IsValid():
            if pointee.name == "void":
                return "rawptr"
            return "^"+type_display(pointee)
        return f"^{name}"
    if t.is_reference: name = f"&{name}"
    return name

def value_summary(value: lldb.SBValue) -> str:
    return value.GetSummary() or value.GetValue() or "<no value>"

def correct_proc_type_display(t: lldb.SBType) -> str:

    type_name = t.name

    # The type name already contains most of what we need
    # e.g., "proc(f:^main::Foo,b:main::Bar)->(ok:bool)"
    # We need to convert it to: "proc (^main.Foo, main.Bar) -> bool"
    
    # Extract calling convention if present
    convention = ""
    if '"' in type_name:
        # Handle "contextless" or other conventions
        conv_start = type_name.find('"')
        conv_end = type_name.find('"', conv_start + 1)
        if conv_start != -1 and conv_end != -1:
            convention = type_name[conv_start:conv_end+1]
    
    # Parse parameters and return types
    # Find the parameter list
    param_start = type_name.find('(')
    param_end = type_name.find(')')
    return_start = type_name.find('->')
    
    if param_start == -1 or param_end == -1:
        return f"proc {convention} <invalid>"
    
    params_str = type_name[param_start+1:param_end]
    
    # Parse parameters - split by comma but handle nested types
    params = []
    if params_str:
        # Simple split for now - this could be improved to handle complex nested types
        param_parts = params_str.split(',')
        for param in param_parts:
            # Extract type after the colon
            if ':' in param:
                param_type = param.split(':', 1)[1].strip()
                # Convert :: to .
                param_type = param_type.replace('::', '.')
                params.append(param_type)
    
    # Parse return type
    return_type = ""
    if return_start != -1:
        return_part = type_name[return_start+2:]
        if return_part.startswith('(') and return_part.endswith(')'):
            # Multiple return values
            return_inner = return_part[1:-1]
            if return_inner:
                return_parts = return_inner.split(',')
                return_types = []
                for ret in return_parts:
                    if ':' in ret:
                        ret_type = ret.split(':', 1)[1].strip()
                        ret_type = ret_type.replace('::', '.')
                        return_types.append(ret_type)
                if len(return_types) == 1:
                    return_type = return_types[0]
                else:
                    return_type = f"({', '.join(return_types)})"
        else:
            # Single return value
            if ':' in return_part:
                return_type = return_part.split(':', 1)[1].strip()
                return_type = return_type.replace('::', '.')
    
    # Build the final string
    params_formatted = ', '.join(params)
    if convention:
        result = f"proc {convention} ({params_formatted})"
    else:
        result = f"proc ({params_formatted})"
    
    if return_type:
        result += f" -> {return_type}"
    
    return result.replace('  ', ' ').strip()  # Clean up extra spaces

def pointer_summary(ptr: lldb.SBValue, _dict) -> str:

    # nil pointer
    if ptr.GetValueAsUnsigned() == 0:
        return "nil"
    
    # raw pointer
    if ptr.type.name == "void *":
        return f"rawptr({ptr.GetValue()})"
    
    # proc pointer
    pointee_type = ptr.type.GetPointeeType()
    if pointee_type.type == lldb.eTypeClassFunction:
        
        params = []
        return_type = None
        
        return_type_obj = pointee_type.GetFunctionReturnType()
        if return_type_obj.IsValid():
            return_type = type_display(return_type_obj)
        
        num_args = pointee_type.GetFunctionArgumentTypes().GetSize()
        for i in range(num_args):
            param_type = pointee_type.GetFunctionArgumentTypes().GetTypeAtIndex(i)
            if param_type.IsValid():
                param_type_str = type_display(param_type)
                params.append(param_type_str)
        
        params_str = ', '.join(params)
        result = f'proc "c" ({params_str})'
        
        if return_type and return_type != "void":
            result += f" -> {return_type}"
        
        return result

    # Regular pointer
    pointee: lldb.SBValue = ptr.Dereference()
    if not pointee.IsValid():
        return type_display(ptr.type)
    
    pointee_summary = pointee.GetSummary()
    if pointee_summary:
        return f"&{pointee_summary}"
    else:
        pointee_type = type_display(ptr.type)
        pointee_value = pointee.GetValue()
        if pointee_value:
            return f"({pointee_type}){pointee_value}"
        else:
            return f"{pointee_type}"

def __lldb_init_module(debugger: lldb.SBDebugger, unused) -> None:
    debugger.HandleCommand("type summary add --python-function odin.pointer_summary --no-value --recognizer-function odin.is_type_pointer")
    debugger.HandleCommand("type summary add --python-function odin.union_summary              --recognizer-function odin.is_type_union")
    debugger.HandleCommand("type synth   add --python-class    odin.UnionChildProvider         --recognizer-function odin.is_type_union")
    debugger.HandleCommand("type summary add --python-function odin.string_summary             --recognizer-function odin.is_type_string")
    debugger.HandleCommand("type synth   add --python-class    odin.SliceChildProvider         --recognizer-function odin.is_type_slice")
    debugger.HandleCommand("type summary add --python-function odin.slice_summary              --recognizer-function odin.is_type_slice")
    debugger.HandleCommand("type synth   add --python-class    odin.MapChildProvider           --recognizer-function odin.is_type_map")
    debugger.HandleCommand("type summary add --python-function odin.struct_summary             --recognizer-function odin.is_type_struct")
