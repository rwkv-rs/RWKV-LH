## Brief Description

There is a triangle with a height of $n$, which is divided into many parts. Some of these parts have been cut out (the shaded areas are the parts that are cut out). Your task is to find the area of the largest complete triangular region remaining.

**The input consists of multiple datasets.** Each dataset begins with an integer $n$, followed by $n$ lines representing a character triangle. The "#" character represents the cut-out parts, and the "-" character represents the remaining parts. The input ends when $n = 0$.

For each dataset, output should consist of two lines: the first line indicates the triangle number, and the second line indicates the area of the largest remaining triangle, formatted as in the example.

## Input/Output Examples

### Input Example #1

```
5
#-##----#
-----#-
---#-
-#-
-
4
#-#-#--
#---#
##-
-
0
```

### Output Example #1

```
Triangle #1
The largest triangle area is 9.
Triangle #2
The largest triangle area is 4.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
