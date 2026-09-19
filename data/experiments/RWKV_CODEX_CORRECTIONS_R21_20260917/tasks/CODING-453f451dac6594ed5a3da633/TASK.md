Consider the following program:

1. Input $n$

2. Output $n$

3. If $n=1$, exit the program

4. If $n$ is odd, set $n \rightarrow 3n + 1$

5. If $n$ is even, set $n \rightarrow \dfrac{n}{2}$

6. Go back to step $2$

For example, if the input is $22$, the output sequence will be: `22 11 34 17 52 26 13 40 20 10 5 16 8 4 2 1`.

We conjecture that, for any positive integer input $n$, the program will eventually output $1$ (this is guaranteed to be true for $n \le 10^6$). Given $n$, you can compute the number of numbers output by this program (including the final $1$). The total number of output numbers is called the cycle length of this $n$. For example, the cycle length for the above case is $16$.

For each input pair $(i,j)$, calculate the maximum cycle length for all numbers in the range $[i,j]$.

## Input Format

Input consists of several pairs of integers $(i,j)$, where it is guaranteed that $0 < i, j \le 10^4$. For each pair $(i,j)$, compute the maximum cycle length within the range $[i,j]$. It is guaranteed that there will be no overflow during calculations within 32-bit integer limits.

## Output Format

For each pair $(i,j)$, first output $i,j$, followed by the maximum cycle length within the range $[i,j]$. Separate each number with a space, then move to a new line.

## Sample Input #1

```
1 10
100 200
201 210
900 1000
```

## Sample Output #1

```
1 10 20
100 200 125
201 210 89
900 1000 174
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
