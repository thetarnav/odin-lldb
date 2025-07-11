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
	bar := Bar{"World", 84}
	enum_value := Enum.Three

	foo_bar_union: Foo_Bar_Union = "yooo"
	foo_bar_union_nil: Foo_Bar_Union
	foo_bar_union_no_nil: Foo_Bar_Union_No_Nill = foo
	foo_bar_union_shared_nil: Foo_Bar_Union_Shared_Nil = &foo

	writer := io.Writer{}

	fmt.println("Enum: ", enum_value)
	fmt.println("Foo: ", foo)
	fmt.println("Bar: ", bar)
	fmt.println("Foo_Bar_Union: ", foo_bar_union)
	fmt.println("Foo_Bar_Union_No_Nill: ", foo_bar_union_no_nil)
	fmt.println("Foo_Bar_Union_Shared_Nil: ", foo_bar_union_shared_nil)
	fmt.println("writer=", writer)

	return
}
