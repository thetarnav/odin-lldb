package main

import "core:fmt"
import "core:io"

Enum :: enum {One, Two, Three}
Foo :: struct {foo_name: string, value: int}
Bar :: struct {bar_name: string, value: int}

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

	bar := Bar{"World", 84}
	// (lldb) p bar
	// (main::Bar) {"World", 84}

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

	foo_bar_union_shared_nil: Foo_Bar_Union_Shared_Nil = &foo
	// (lldb) p foo_bar_union_shared_nil
	// (main::Foo_Bar_Union_Shared_Nil) ^main.Foo(&{"Hello", 42})

	writer := io.Writer{}
	// (lldb) p writer
	// (io::Stream) {nil, nil}

	// (lldb) p writer.procedure
	// (io::Stream_Proc) nil
	
	// (lldb) p writer.data
	// (void *) nil

	breakpoint() // for lldb to breakpoint here
	return
}

@(link_name="breakpoint")
breakpoint :: proc () {}
