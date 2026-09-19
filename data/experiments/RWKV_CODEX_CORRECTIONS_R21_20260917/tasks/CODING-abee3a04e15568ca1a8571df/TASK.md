(Excerpted from "Introduction to Algorithm Competition Training Guide" by Liu Rujia and Chen Feng)

Given a rectangular piece of chocolate with a length of $x$ and a width of $y$, each operation allows you to cut the chocolate along a straight line into two pieces, each having integer dimensions (you cannot cut multiple pieces in one operation).

The question is: Is it possible to perform several operations to obtain $n$ pieces of chocolate with areas $a_1, a_2, ..., a_n$?

## Input and Output Format

**Input Format:**

The input consists of several sets of data:

- Each data set begins with an integer $n (1 \leq n \leq 15)$;
- followed by two integers $x, y (1 \leq x, y \leq 100)$;
- and then $n$ integers $a_1, a_2, ..., a_n$.

The end of the input is indicated by $n = 0$.

**Output Format:**

For each data set, output `Yes` if the cutting is successful, otherwise output `No`.

## Sample Input

### Input Sample #1

```
4
3 4
6 3 2 1
2
2 3
1 5
0
```

## Sample Output

### Output Sample #1

```
Case 1: Yes
Case 2: No
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
