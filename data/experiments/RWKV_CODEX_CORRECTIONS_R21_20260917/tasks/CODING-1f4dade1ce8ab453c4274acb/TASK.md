In a spreadsheet with R rows and C columns (R≤20, C≤10), the row labels are A-T and the column labels are 0-9. Input the contents of each cell in row-major order. Each cell may contain an integer (which can be negative) or an expression involving other cells (containing only non-negative integers, cell names, and addition/subtraction operators, without parentheses). The cell content is guaranteed to start with a cell name, contain no whitespace, and be at most 75 characters long.

Calculate the value of all expressions as much as possible, then output the values of each cell (the calculation result is guaranteed to be an integer with an absolute value not exceeding 10000). If there are any circular references among cells, output them after the table (still in row-major order), as shown in the example.

Translation provided by: BFD_qt

## Input and Output Examples

### Input Example #1

```
2 2
A1+B1
5
3
B0-A1
3 2
A0
5
C1
7
A1+B1
B0+A1
0 0
```

### Output Example #1

```
0
1
A
3
5
B
3 -2
A0: A0
B0: C1
C1: B0+A1
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
