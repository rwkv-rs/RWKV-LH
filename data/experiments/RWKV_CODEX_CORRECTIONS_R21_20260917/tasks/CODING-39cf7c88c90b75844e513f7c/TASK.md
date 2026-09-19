Given a valid Pascal source program, output it according to the following rules:

- Replace every sequence of spaces (except for spaces within string literals) with a single space. A string literal is defined as a sequence enclosed in single quotes `'` and contains at least one character. Note that two consecutive single quotes `''` represent a single quote character.

- Remove all comments and empty lines. A comment is defined as text starting with `*` and ending with `*`, or starting with `{` and ending with `}`. Also, remove any lines that are completely blank.

You are guaranteed that the input consists of visible characters and does not contain any `Tab` characters.

## Input and Output Example

### Input Example #1

```
Program Test (input, output);
{ this is a great program }
Var
X, Y
:
integer
;
begin
readln (X, Y);
writeln (X, ' This is Y ', Y,
end.
"Hi!') ;
```

### Output Example #1

```
Program Test (input, output);
Var X, Y : integer ;
begin
readln (X, Y);
writeln (X, ' This is Y ', Y, "Hi!') ;
end.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
