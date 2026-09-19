#### Description

The following is pseudocode for constructing a sequence of fractions:

```
for d = 1 to infinity do
    for n = 0 to d do
        if gcd(n,d) = 1 then print n / d
```

Using this code, an infinite sequence of fractions can be constructed.

However, a character named Shuchong doesn't know how to calculate the $k$-th term.   
Therefore, they have come to you for help!

#### Input

**Multiple test cases.**   
Each test case consists of a single integer $k$ on a line, with a value of $0$ indicating the termination of the input.

#### Output

For each test case, output a line containing two integers $n,d$ representing the $k$-th term of the sequence.

#### Limitation

For $100\%$ of the test data, $1 \le k \le 12158598919$.

#### Source

Translated by Yizhi Shuchongzai.

## Input/Output Example

### Input Example #1

```
1
2
3
12158598919
0
```

### Output Example #1

```
0/1
1/1
1/2
199999/200000
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
