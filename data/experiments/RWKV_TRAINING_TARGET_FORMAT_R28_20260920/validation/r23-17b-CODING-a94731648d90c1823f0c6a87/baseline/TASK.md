Little D likes numbers that have a specific property:
Let $n$ be a positive integer, and $S(n)$ be the sum of its digits. Define

$$D(n)\begin{cases}\displaystyle S(n), S(n)<10 \\\displaystyle D(S(n)), S(n)>10\end{cases}$$

A number that Little D likes can always be expressed in the form $x \times D(x)$ (i.e., if a number A is liked, then there exists a number $x$ such that $A = x \times D(x)$).
Little D wants to know how many numbers he likes within the interval [L, R].

## Input Format

The first line contains an integer T, representing the number of test cases.

Each of the following T lines contains two numbers L and R (guaranteed to be valid intervals), representing the query for the interval [L, R].

## Output Format

Output T lines, each containing a single number, representing how many numbers Little D likes within the corresponding interval.

Your output must exactly match the standard output to score full points for that test case.

## Sample Input and Output

### Input Sample #1

```
3
1 5
3 9
8 8
```

### Output Sample #1

```
2
2
0
```

## Notes/Hints

L, R <= $10^{18}$, T <= 20

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
