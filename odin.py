"""
Python script to visualize Odin slices, maps, strings, etc. in LLDB.

Based on harold-b's script: https://gist.github.com/harold-b/ef16a5c3ebcceccfc2bc7a5c5dd0058d
and laytan's script: https://gist.github.com/laytan/a94c323a84cef7bcfbdf6d21987fd5a9

Repository: https://github.com/thetarnav/odin-lldb
"""

from webbrowser import get
import lldb
import math
import enum
from collections.abc import Callable


def __lldb_init_module(debugger: lldb.SBDebugger, unused) -> None:
    debugger.HandleCommand("type summary add --python-function odin.struct_summary             --recognizer-function odin.is_type_struct")
    debugger.HandleCommand("type summary add --python-function odin.pointer_summary --no-value --recognizer-function odin.is_type_pointer")
    debugger.HandleCommand("type summary add --python-function odin.union_summary              --recognizer-function odin.is_type_union")
    debugger.HandleCommand("type synth   add --python-class    odin.Union_Children_Provider    --recognizer-function odin.is_type_union")
    debugger.HandleCommand("type summary add --python-function odin.string_summary             --recognizer-function odin.is_type_string")
    debugger.HandleCommand("type synth   add --python-class    odin.Slice_Children_Provider    --recognizer-function odin.is_type_slice")
    debugger.HandleCommand("type summary add --python-function odin.slice_summary              --recognizer-function odin.is_type_slice")
    debugger.HandleCommand("type summary add --python-function odin.array_summary              --recognizer-function odin.is_type_array")
    debugger.HandleCommand("type synth   add --python-class    odin.Map_Children_Provider      --recognizer-function odin.is_type_map")
    debugger.HandleCommand("type summary add --python-function odin.map_summary                --recognizer-function odin.is_type_map")


class Odin_Type(enum.Enum):
    SLICE   = "slice"
    ARRAY   = "array"
    STRING  = "string" 
    MAP     = "map"
    STRUCT  = "struct"
    PTR     = "pointer"
    OTHER   = "other"

def get_odin_type(t: lldb.SBType) -> Odin_Type:
    
    if t.type == lldb.eTypeClassStruct:
        if t.name == "string":
            return Odin_Type.STRING
        
        if (
            (t.name.startswith("[]") or t.name.startswith("[dynamic]")) and
            not t.name.endswith(']')
        ):
            return Odin_Type.SLICE
        
        if t.name.startswith("map["):
            return Odin_Type.MAP

        return Odin_Type.STRUCT

    if t.type == lldb.eTypeClassArray:
        return Odin_Type.ARRAY

    if t.is_pointer:
        return Odin_Type.PTR
    
    return Odin_Type.OTHER

def is_type_slice  (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.SLICE
def is_type_string (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.STRING
def is_type_map    (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.MAP
def is_type_struct (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.STRUCT
def is_type_pointer(t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.PTR
def is_type_array  (t: lldb.SBType, _dict) -> bool: return get_odin_type(t) == Odin_Type.ARRAY

def type_get_field_at(t: lldb.SBType, idx: int) -> lldb.SBTypeMember:
    return t.GetFieldAtIndex(idx)

def value_get_child_at(v: lldb.SBValue, idx: int) -> lldb.SBValue:
    return v.GetChildAtIndex(idx)

def value_get_child(v: lldb.SBValue, name: str) -> lldb.SBValue:
    return v.GetChildMemberWithName(name)

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
    if not value.IsValid():
        return "<invalid value>"
    return value.GetSummary() or value.GetValue() or "<no value>"

AGGREGATE_SUMMARY_MAX_LEN = 50
SLICE_CHUNK_SIZE          = 1000

def aggregate_value_summary(
    prefix:    str,
    suffix:    str,
    get_value: Callable[[int], str],
    length:    int,
) -> str:
    summary = prefix
    
    for i in range(length):
        item = get_value(i)
        
        separator = ", " if i > 0 else ""
        new_length = len(summary) + len(separator) + len(item) + len(suffix)

        if new_length > AGGREGATE_SUMMARY_MAX_LEN and i > 0:
            summary += "..."
            break

        summary += separator + item

    return summary + suffix


# ------------------------------------------------------------------------------
# Struct Values
#
# Default for any struct type that is not a built-in type.

def struct_summary(v: lldb.SBValue, _dict) -> str:
    v = v.GetNonSyntheticValue()

    return aggregate_value_summary("{", "}",
        get_value=lambda i: value_summary(v.GetChildAtIndex(i)),
        length=v.num_children,
    )


# ------------------------------------------------------------------------------
# Slice Values
# 
# handles both slices and dynamic arrays
# since the layout is the same:
# 
#    Raw_Slice :: struct($T: typeid) {
#        data: [^]T,
#        len:  int,
#    }
# 
#    Raw_Dynamic_Array :: struct($T: typeid) {
#        data:      [^]T,
#        len:       int,
#        cap:       int,
#        allocator: ^runtime.Allocator,
#    }

def get_len(v: lldb.SBValue) -> int:
    return value_get_child(v.GetNonSyntheticValue(), "len").signed

def get_cap(v: lldb.SBValue) -> int:
    return value_get_child(v.GetNonSyntheticValue(), "cap").signed

def get_data(v: lldb.SBValue) -> lldb.SBValue:
    return value_get_child(v.GetNonSyntheticValue(), "data")

def slice_summary(v: lldb.SBValue, _dict) -> str:

    length = get_len(v)

    # GetChildAtIndex goes through Slice_Children_Provider
    if length > SLICE_CHUNK_SIZE:
        get_value = lambda i: value_summary(v.GetChildAtIndex(i // SLICE_CHUNK_SIZE) \
                                             .GetChildAtIndex(i % SLICE_CHUNK_SIZE))
    else:
        get_value = lambda i: value_summary(v.GetChildAtIndex(i))

    return aggregate_value_summary(f"[{length}]{{", "}", get_value, length)

class Slice_Children_Provider(lldb.SBSyntheticValueProvider):

    def __init__(self, val: lldb.SBValue, _dict) -> None:
        self.val = val

    def update(self) -> None:
        self.len  = get_len(self.val)
        self.data = get_data(self.val)
        assert self.data.type.is_pointer

        self.chunked_len = 0 if not self.len > SLICE_CHUNK_SIZE else math.ceil(self.len / SLICE_CHUNK_SIZE)

    def has_children(self) -> bool:
        return self.len > 0

    def num_children(self) -> int:
        return self.chunked_len if self.chunked_len > 0 else self.len

    def get_child_at_index(self, idx: int) -> lldb.SBValue:
        length = self.num_children()
        assert idx >= 0 and idx < length

        pointee = self.data.deref

        if self.chunked_len > 0:
            array_len   = min(SLICE_CHUNK_SIZE, self.len - idx * SLICE_CHUNK_SIZE)
            range_start = idx * SLICE_CHUNK_SIZE
            name        = f"[{range_start}..<{range_start+array_len}]"
            offset      = idx * pointee.size * SLICE_CHUNK_SIZE
            type        = pointee.type.GetArrayType(array_len)
        else:
            name        = f"[{idx}]"
            offset      = idx * pointee.size
            type        = pointee.type

        return self.data.CreateChildAtOffset(name, offset, type)


# ------------------------------------------------------------------------------
# Array Values

def array_summary(v: lldb.SBValue, _dict) -> str:
    v = v.GetNonSyntheticValue() if v.IsSynthetic() else v

    length = v.num_children

    return aggregate_value_summary(f"[{length}]{{", "}",
        get_value=lambda i: value_summary(v.GetChildAtIndex(i)),
        length=length,
    )


# ------------------------------------------------------------------------------
# String Values
# 
# Same layout as a slice,
#    Raw_String :: struct {
#        data: [^]u8,
#        len:  int,
#    }
# 
# Odin strings are UTF-8 encoded

def string_summary(v: lldb.SBValue, _dict) -> str:

    length  = get_len(v)
    if length == 0:
        return '""'

    pointer = get_data(v).GetValueAsUnsigned(0)
    if pointer == 0:
        return struct_summary(v, _dict)

    error = lldb.SBError()
    string_data = v.process.ReadMemory(pointer, length, error)
    if not error.success:
        print(f"Error reading string data: {error}")
        return "<error reading string>"

    return '"{}"'.format(string_data.decode("utf-8"))


# ------------------------------------------------------------------------------
# Map Values

def map_summary(v: lldb.SBValue, _dict) -> str:

    length = get_len(v.GetNonSyntheticValue())
    if length == 0:
        return "map[0]{}"

    return aggregate_value_summary(
        f"map[{length}]{{", "}",
        get_value=lambda i: f"{value_summary(v.GetChildAtIndex(i*2))} = {value_summary(v.GetChildAtIndex(i*2 + 1))}",
        length=length,
    )

class Map_Children_Provider:

    def __init__(self, val, dict):
        self.val = val

    def num_children(self):
        return get_len(self.val) * 2 + 1

    def get_child_at_index(self, index):
        data       = self.val.GetChildMemberWithName("data")
        tkey       = data.GetChildMemberWithName("key").type
        tval       = data.GetChildMemberWithName("value").type
        hash_field = data.GetChildMemberWithName("hash")
        key_cell   = data.GetChildMemberWithName("key_cell")
        value_cell = data.GetChildMemberWithName("value_cell")

        raw_data   = data.GetValueAsUnsigned()
        key_ptr    = raw_data & ~63
        cap_log2   = raw_data & 63
        cap        = 0 if cap_log2 <= 0 else 1 << cap_log2

        key_cell_info   = cell_info(tkey, key_cell)
        value_cell_info = cell_info(tval, value_cell)

        size_of_hash = hash_field.size
        assert size_of_hash == 8
    
        value_ptr = cell_index(key_ptr, key_cell_info, cap)
        hash_ptr  = cell_index(value_ptr, value_cell_info, cap)

        error = lldb.SBError()

        # Last one, the capacity.
        if index == self.num_children()-1:
            cap_data = lldb.SBData.CreateDataFromInt(cap)
            return self.val.CreateValueFromData("cap", cap_data, self.val.GetChildMemberWithName("len").type)

        wants_key = index % 2 == 0
        index = int(index / 2)

        key_index = 0
        for i in range(cap):
            tombstone_mask = 1 << (size_of_hash*8 - 1)

            offset_hash = hash_ptr + i * size_of_hash

            hash_val = self.val.process.ReadUnsignedFromMemory(offset_hash, size_of_hash, error)
            if not error.success:
                print(error)
                continue
            elif hash_val == 0 or (hash_val & tombstone_mask) != 0:
                continue

            offset_key   = cell_index(key_ptr, key_cell_info, i)
            offset_value = cell_index(value_ptr, value_cell_info, i)

            if index == key_index:
                if wants_key:
                    return self.val.CreateValueFromAddress(f"[{i}]", offset_key, tkey)
                else:
                    return self.val.CreateValueFromAddress(f"[{i}]", offset_value, tval)

            key_index += 1

        print("not found")

def cell_info(typev, cell_type) -> 'Cell_Info':
    elements_per_cell = 0

    if typev.size != cell_type.size:
        array_type = cell_type.children[0].type
        if array_type.size > 0 and typev.size > 0:
            elements_per_cell = array_type.size / typev.size

    if elements_per_cell == 0:
        elements_per_cell = 1

    return Cell_Info(typev.size, cell_type.size, elements_per_cell)

def cell_index(base: int, info: "Cell_Info", index: int) -> int:
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
        cell_index = index // info.elements_per_cell;
        data_index = index % info.elements_per_cell;

    return base + (cell_index * info.size_of_cell) + (data_index * info.size_of_type);

class Cell_Info:
    def __init__(self, size_of_type: int, size_of_cell: int, elements_per_cell: int) -> None:
        self.size_of_type      = size_of_type
        self.size_of_cell      = size_of_cell
        self.elements_per_cell = elements_per_cell


# ------------------------------------------------------------------------------
# Union Values

# Layout:
#    normal & #shared_nil union type:
#        tag: u64
#        v1:  T0
#        v2:  T1
#        ...
#    #no_nil union type:
#        tag: u64
#        v0:  T0
#        v1:  T1
#        ...

def is_type_union  (t: lldb.SBType, _dict) -> bool:
    if t.type == lldb.eTypeClassUnion:
        tag = type_get_field_at(t, 0)
        if tag.IsValid() and tag.name == "tag":
            return True
    return False

def union_is_no_nil(t: lldb.SBType) -> bool:
    first = type_get_field_at(t, 1)
    return first.IsValid() and first.name == "v0"

def union_variant(v: lldb.SBValue) -> lldb.SBValue | None:
    if v.IsSynthetic():
        v = v.GetNonSyntheticValue()

    tag = v.GetChildAtIndex(0)
    assert(tag.name == "tag")

    tag_value = tag.unsigned
    
    is_no_nil = union_is_no_nil(v.type)

    if not is_no_nil and tag_value == 0:
        return None
    
    return v.GetChildMemberWithName(f"v{tag_value}")

def union_summary(v: lldb.SBValue, _dict) -> str:
    variant = union_variant(v)
    if variant is None:
        return "nil"

    return f"{type_display(variant.type)}({value_summary(variant)})"

class Union_Children_Provider(lldb.SBSyntheticValueProvider):
    def __init__(self, val: lldb.SBValue, _dict) -> None:
        self.val = val

    def update(self) -> None:
        self.variant = union_variant(self.val)

    def has_children(self) -> bool:
        return self.variant.MightHaveChildren() if self.variant else False

    def num_children(self) -> int:
        return self.variant.num_children if self.variant else 0

    def get_child_at_index(self, idx) -> lldb.SBValue | None:
        return self.variant.GetChildAtIndex(idx) if self.variant else None
    
    def get_child_index(self, name) -> None | int:
        return self.variant.GetIndexOfChildWithName(name) if self.variant else None



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
    pointee_type: lldb.SBType = ptr.type.GetPointeeType()
    if pointee_type.type == lldb.eTypeClassFunction:
        
        params = []
        return_type = None
        
        return_type_obj = pointee_type.GetFunctionReturnType()
        if return_type_obj.IsValid():
            return_type = type_display(return_type_obj)
        
        for param_type in pointee_type.GetFunctionArgumentTypes():
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
        pointee_type_str = type_display(ptr.type)
        pointee_value = pointee.GetValue()
        if pointee_value:
            return f"({pointee_type_str}){pointee_value}"
        else:
            return f"{pointee_type_str}"
