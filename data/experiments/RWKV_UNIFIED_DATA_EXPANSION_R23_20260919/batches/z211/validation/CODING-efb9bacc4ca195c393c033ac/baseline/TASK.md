Similar to P1597. Each line consists of a statement, which can be an assignment statement in the form of `<variable> := <expression>`, a print statement in the form of `PRINT <variable>`, or a reset statement as `RESET`.

For assignment statements, only addition, subtraction, and multiplication operations will be used. You need to update the value of the variable on the left side of the statement to the value of the expression.

For print statements, you must output the value of the given variable. If the variable has not been defined, output `UNDEF`.

For reset statements, you should clear all previous operations, effectively resetting as if nothing had previously occurred.

## Input/Output Example

### Input Example #1

```
a := b + c
b := 3
c := 5
PRINT d
PRINT a
b := 8
PRINT a
RESET
PRINT a
```

### Output Example #1

```
UNDEF
8
13
UNDEF
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
