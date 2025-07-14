package main

import "core:fmt"
import "core:io"

Enum :: enum {One, Two, Three}
Foo :: struct {foo_name: string, value: int}
Bar :: struct {value: int, bar_name: string}

Foo_Bar_Union :: union {Foo, Bar, string}
Foo_Bar_Union_No_Nill :: union #no_nil {Foo, Bar}
Foo_Bar_Union_Shared_Nil :: union #shared_nil {Enum, ^Foo, ^Bar}

main :: proc () {

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

	foo_slice := []Foo{{"Slice1", 1}, {"Slice2", 2}}
	// (lldb) p foo_slice
	// ([]main::Foo) [2]{{"Slice1", 1}, {"Slice2", 2}}

	// (lldb) frame variable foo_slice[0] foo_slice[1]
	// (main::Foo) foo_slice[0] = {"Slice1", 1}
	// (main::Foo) foo_slice[1] = {"Slice2", 2}

	foo_long_slice := []Foo{{"Slice1", 1}, {"Slice2", 2}, {"Slice3", 3}, {"Slice4", 4}, {"Slice5", 5}}
	// (lldb) p foo_long_slice
	// ([]main::Foo) [5]{{"Slice1", 1}, {"Slice2", 2}, {"Slice3", 3}...}

	slice_empty := []Foo{}
	// (lldb) p slice_empty
	// ([]main::Foo) [0]{}

	breakpoint() // for lldb to breakpoint here
	return
}

@(link_name="breakpoint")
breakpoint :: proc () {}
