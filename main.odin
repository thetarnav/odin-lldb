package main

import "core:fmt"

main :: proc () {

	Enum :: enum {One, Two, Three}
	Foo :: struct {foo: string}
	Bar :: struct {bar: string}

	Foo_Bar_Union :: union {Foo, Bar}
	Foo_Bar_Union_No_Nill :: union #no_nil {Foo, Bar}
	Foo_Bar_Union_Shared_Nil :: union #shared_nil {Enum, ^Foo, ^Bar}

	foo := Foo{"Hello"}
	bar := Bar{"World"}
	enum_value := Enum.Three

	foo_bar_union: Foo_Bar_Union = foo
	foo_bar_union_no_nil: Foo_Bar_Union_No_Nill = foo
	foo_bar_union_shared_nil: Foo_Bar_Union_Shared_Nil = &foo

	fmt.println("Enum: ", enum_value)
	fmt.println("Foo: ", foo)
	fmt.println("Bar: ", bar)
	fmt.println("Foo_Bar_Union: ", foo_bar_union)
	fmt.println("Foo_Bar_Union_No_Nill: ", foo_bar_union_no_nil)
	fmt.println("Foo_Bar_Union_Shared_Nil: ", foo_bar_union_shared_nil)

	return
}
