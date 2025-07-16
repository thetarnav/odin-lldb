#+feature dynamic-literals
package main

import "base:runtime"
import "core:fmt"
import "core:io"

Enum :: enum {One, Two, Three}

Foo :: struct {foo_name: string, value: int}
Bar :: struct {value: int, bar_name: string}

Struct_Empty :: struct {}
Struct_Long  :: struct {a, b, c, d, e, f: int}

Foo_Bar_Union            :: union {Foo, Bar, string}
Foo_Bar_Union_No_Nill    :: union #no_nil {Foo, Bar}
Foo_Bar_Union_Shared_Nil :: union #shared_nil {Enum, ^Foo, ^Bar}

main :: proc () {

	struct_empty := Struct_Empty{}
	// (lldb) p struct_empty
	// (main::Struct_Empty) {}

	struct_long := Struct_Long{100000001, 100000002, 100000003, 100000004, 100000005, 100000006}
	// (lldb) p struct_long
	// (main::Struct_Long) {100000001, 100000002, 100000003, 100000004, 100000005...}

	str_empty := ""
	// (lldb) p str_empty
	// (string) ""

	str_nil: string
	// (lldb) p str_nil
	// (string) ""

	str_raw: runtime.Raw_String = {len = 10}
	// (lldb) p str_raw
	// (runtime::Raw_String) {nil, 10}

	str_nil_with_len := transmute(string)str_raw
	// (lldb) p str_nil_with_len
	// (string) {nil, 10}

	foo := Foo{"Hello", 42}
	// (lldb) p foo
	// (main::Foo) {"Hello", 42}

	// (lldb) p foo.foo_name
	// (string) "Hello"

	foo_ptr := &foo
	// (lldb) p foo_ptr
	// (main::Foo *) &{"Hello", 42}

	foo_raw_ptr := rawptr(foo_ptr)
	// (lldb) p foo_raw_ptr
	// (void *) rawptr(%PTR%)

	bar := Bar{84, "World"}
	// (lldb) p bar
	// (main::Bar) {84, "World"}

	enum_value := Enum.Three
	// (lldb) p enum_value
	// (main::Enum) Three

	foo_bar_union: Foo_Bar_Union = "hello world"
	// (lldb) p foo_bar_union
	// (main::Foo_Bar_Union) string("hello world")

	foo_bar_union_nil: Foo_Bar_Union
	// (lldb) p foo_bar_union_nil
	// (main::Foo_Bar_Union) nil

	foo_bar_union_no_nil: Foo_Bar_Union_No_Nill = foo
	// (lldb) p foo_bar_union_no_nil
	// (main::Foo_Bar_Union_No_Nill) main.Foo({"Hello", 42})

	// (lldb) frame variable foo_bar_union_no_nil[0] foo_bar_union_no_nil[1]
	// (string) foo_bar_union_no_nil[0] = "Hello"
	// (int) foo_bar_union_no_nil[1] = 42

	foo_bar_union_shared_nil: Foo_Bar_Union_Shared_Nil = &bar
	// (lldb) p foo_bar_union_shared_nil
	// (main::Foo_Bar_Union_Shared_Nil) ^main.Bar(&{84, "World"})

	// (lldb) frame variable foo_bar_union_shared_nil[0] foo_bar_union_shared_nil[1]
	// (int) foo_bar_union_shared_nil[0] = 84
	// (string) foo_bar_union_shared_nil[1] = "World"

	writer := io.Writer{}
	// (lldb) p writer
	// (io::Stream) {nil, nil}

	// (lldb) p writer.procedure
	// (io::Stream_Proc) nil
	
	// (lldb) p writer.data
	// (void *) nil

	foo_proc := proc (f: ^Foo, b: Bar) {return}
	// (lldb) p foo_proc
	// (proc(f:^main::Foo,b:main::Bar)) proc "c" (^main.Foo, main.Bar, ^runtime.Context)

	foo_proc_ok := proc (f: ^Foo, b: Bar) -> (ok: bool) {return}
	// (lldb) p foo_proc_ok
	// (proc(f:^main::Foo,b:main::Bar)->(ok:bool)) proc "c" (^main.Foo, main.Bar, ^runtime.Context) -> bool

	foo_proc_multi_res := proc (f: Foo, b: Bar) -> (idx: int, ok: bool) {return}
	// (lldb) p foo_proc_multi_res
	// (proc(f:main::Foo,b:main::Bar)->(idx:int,ok:bool)) proc "c" (main.Foo, main.Bar, int, ^runtime.Context) -> bool

	foo_bar_contextless := proc "contextless" (f: Foo, b: Bar) -> (idx: int, ok: bool) {return}
	// (lldb) p foo_bar_contextless
	// (proc"contextless"(f:main::Foo,b:main::Bar)->(idx:int,ok:bool)) proc "c" (main.Foo, main.Bar, int) -> bool

	slice := []Foo{{"Slice1", 1}, {"Slice2", 2}}
	// (lldb) p slice
	// ([]main::Foo) [2]{{"Slice1", 1}, {"Slice2", 2}}

	// (lldb) frame variable slice[0] slice[1]
	// (main::Foo) slice[0] = {"Slice1", 1}
	// (main::Foo) slice[1] = {"Slice2", 2}

	slice_long := []Foo{{"Slice1", 1}, {"Slice2", 2}, {"Slice3", 3}, {"Slice4", 4}, {"Slice5", 5}}
	// (lldb) p slice_long
	// ([]main::Foo) [5]{{"Slice1", 1}, {"Slice2", 2}, {"Slice3", 3}...}

	slice_empty := []Foo{}
	// (lldb) p slice_empty
	// ([]main::Foo) [0]{}

	array := [2]Foo{{"Array1", 1}, {"Array2", 2}}
	// (lldb) p array
	// (main::Foo[2]) [2]{{"Array1", 1}, {"Array2", 2}}

	// (lldb) frame variable array[0] array[1]
	// (main::Foo) array[0] = {"Array1", 1}
	// (main::Foo) array[1] = {"Array2", 2}

	array_long := [5]Foo{{"Array1", 1}, {"Array2", 2}, {"Array3", 3}, {"Array4", 4}, {"Array5", 5}}
	// (lldb) p array_long
	// (main::Foo[5]) [5]{{"Array1", 1}, {"Array2", 2}, {"Array3", 3}...}

	array_empty := [0]Foo{}
	// (lldb) p array_empty
	// (main::Foo[]) [0]{}

	dynamic_array := [dynamic]Foo{Foo{"Dynamic1", 1}, Foo{"Dynamic2", 2}}
	// (lldb) p dynamic_array
	// ([dynamic]main::Foo) [2]{{"Dynamic1", 1}, {"Dynamic2", 2}}

	// (lldb) frame variable dynamic_array[0] dynamic_array[1]
	// (main::Foo) dynamic_array[0] = {"Dynamic1", 1}
	// (main::Foo) dynamic_array[1] = {"Dynamic2", 2}

	dynamic_array_long := [dynamic]Foo{Foo{"Dynamic1", 1}, Foo{"Dynamic2", 2}, Foo{"Dynamic3", 3}, Foo{"Dynamic4", 4}, Foo{"Dynamic5", 5}}
	// (lldb) p dynamic_array_long
	// ([dynamic]main::Foo) [5]{{"Dynamic1", 1}, {"Dynamic2", 2}, {"Dynamic3", 3}...}

	dynamic_array_chunked: [dynamic]Foo
	for i in 0..<10_000 {
		append(&dynamic_array_chunked, Foo{"DynamicChunked", i})
	}

	// (lldb) p dynamic_array_chunked
	// ([dynamic]main::Foo) [10000]{{"DynamicChunked", 0}, {"DynamicChunked", 1}...}

	// (lldb) frame variable dynamic_array_chunked[0] dynamic_array_chunked[0][0]
	// (main::Foo[1000]) dynamic_array_chunked[0] = [1000]{{"DynamicChunked", 0}, {"DynamicChunked", 1}...}
	// (main::Foo) dynamic_array_chunked[0][0] = {"DynamicChunked", 0}

	// (lldb) frame variable dynamic_array_chunked[1] dynamic_array_chunked[1][0]
	// (main::Foo[1000]) dynamic_array_chunked[1] = [1000]{{"DynamicChunked", 1000}, {"DynamicChunked", 1001}...}
	// (main::Foo) dynamic_array_chunked[1][0] = {"DynamicChunked", 1000}

	str_map: map[string]Foo = {
		"key1" = {"Value1", 1},
		"key2" = {"Value2", 2},
		"key3" = {"Value3", 3},
	}
	// (lldb) p str_map
	// (map[string]main::Foo) map[3]{"key3" = {"Value3", 3}, "key1" = {"Value1", 1}...}

	breakpoint() // for lldb to breakpoint here
	return
}

@(link_name="breakpoint")
breakpoint :: proc () {}
