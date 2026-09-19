## Problem Description

Given a system of linear equations with two variables, solve for $x$ and $y$.

The equations are provided in the form `ax+by=c`, where $a, b, c$ are integers that may be negative. The solutions for $x$ and $y$ are guaranteed to be integers.

Here is an example. For the system of equations:
```plaintext
-2x+3y=4
x-y=-1
```

You should solve for $x=1, y=2$.

## Input Format

Two lines, each representing an equation.

Each equation may be in one of the following forms:

- `ax+by=c`
- `ax-by=c`
- `-ax+by=c`
- `-ax-by=c`

Here, `c` may be positive, negative, or zero. Terms like `x` or `-x` may appear.

## Output Format

Two lines, each containing an integer, representing $x$ and $y$ respectively.

## Sample Input and Output

### Sample Input #1

```
-2x+3y=4
x-y=-1
```

### Sample Output #1

```
1
2
```

### Sample Input #2

```
3x-5y=-21
-5x+20y=70
```

### Sample Output #2

```
-2
3
```

### Sample Input #3

```
6x+7y=30
-x-y=-5
```

### Sample Output #3

```
5
0
```

## Notes

**Data Range and Constraints**

For $100\%$ of the data, the absolute values of the coefficients do not exceed $100$, and the absolute values of $x$ and $y$ do not exceed $100$. The system is guaranteed to have a unique solution.

**Hint**  

The more complex the classification discussion, the higher the likelihood of bugs in the program.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
