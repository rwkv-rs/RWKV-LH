The `unixfmt` program reads lines of text, combining and breaking lines to create an output file with lines that are as close as possible to, but do not exceed, 72 characters long. The rules for combining and breaking lines are as follows:

1. A new line may be started anywhere there is a space in the input. If a new line is started, there will be no trailing spaces at the end of the previous line or at the beginning of the new line.

2. A line break in the input may be eliminated in the output, provided it is not followed by a space or another line break. If a line break is eliminated, it is replaced by a space.

3. Spaces never appear at the end of a line.

4. If a sequence longer than 72 characters occurs without spaces or line breaks, it appears on a line by itself.

## Input and Output Example

### Input Example #1

```
Unix fmt
The unix fmt program reads lines of text, combining
and breaking lines so as to create an
output file with lines as close to without exceeding
72 characters long as possible. The rules for combining and breaking
lines are as follows.
1. A new line may be started anywhere there is a space in the input.
If a new line is started, there will be no trailing blanks at the
end of the previous line or at the beginning of the new line.
2. A line break in the input may be eliminated in the output, provided
it is not followed by a space or another line break. If a line
break is eliminated, it is replaced by a space.
```

### Output Example #1

```
Unix fmt
The unix fmt program reads lines of text, combining and breaking lines
so as to create an output file with lines as close to without exceeding
72 characters long as possible. The rules for combining and breaking
lines are as follows.
1. A new line may be started anywhere there is a space in the
input. If a new line is started, there will be no trailing blanks at
the end of the previous line or at the beginning of the new line.
2. A line break in the input may be eliminated in the output,
provided it is not followed by a space or another line break. If a
line break is eliminated, it is replaced by a space.
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
