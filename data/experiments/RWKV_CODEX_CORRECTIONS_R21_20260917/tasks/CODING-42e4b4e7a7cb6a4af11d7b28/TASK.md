Given a number, determine whether it is a floating-point number in Pascal.

## Input and Output Examples

### Input Example #1

```
1.2
1.
1.0e-55
e-12
6.5E
1e-12
+4.1234567890E-99999
7.6e+12.5
99
*
```

### Output Example #1

```
1.2 is legal.
1. is illegal.
1.0e-55 is legal.
e-12 is illegal.
6.5E is illegal.
1e-12 is legal.
+4.1234567890E-99999 is legal.
7.6e+12.5 is illegal.
99 is illegal.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
