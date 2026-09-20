Eva is a third-grade elementary school student. She has just learned how to perform addition and subtraction of arbitrary-precision integers. Her homework is to evaluate some expressions. It is boring, so she decided to add a little trick to the homework. Eva wants to add some plus and minus signs to the expression to make its value as large as possible.

## Input Format

The single line of the input file contains the original arithmetic expression. It contains only digits, plus ('+') and minus ('-') signs.

The original expression is correct, that is:

1. Numbers have no leading zeroes.
2. There are no two consecutive signs.
3. The last character of the expression is a digit.

The length of the original expression does not exceed 1000 characters.

## Output Format

Output a single line -- the original expression with some plus and minus signs added. The output expression must satisfy the same correctness constraints as the original one. Its value must be as large as possible.

## Sample Input and Output

### Sample Input #1

```
10+20-30
```

### Sample Output #1

```
10+20-3+0
```

### Sample Input #2

```
-3-4-1
```

### Sample Output #2

```
-3-4-1
```

### Sample Input #3

```
+10
```

### Sample Output #3

```
+10
```

## Notes

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
