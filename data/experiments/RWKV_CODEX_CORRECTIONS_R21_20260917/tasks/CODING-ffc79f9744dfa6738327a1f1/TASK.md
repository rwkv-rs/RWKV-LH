Yazid loves big bowls of wide noodles. There are $m$ bowls of wide noodles, where the $i$-th bowl ($1 \le i \le m$) contains $n_i$ noodles, with their widths being $A_{i,1}, A_{i,2}, \cdots, A_{i,n_i}$.

Let $f(u,v)$ denote the width of the $\left\lfloor\dfrac{n_u + n_v + 1}{2}\right\rfloor$-th smallest noodle in the super-sized bowl of noodles obtained by mixing the $u$-th and $v$-th bowls ($\lfloor x \rfloor$ denotes the largest integer not exceeding $x$).

Yazid wants to compute all $f(u,v)$, but to save time for output, you only need to calculate for all $1 \le u \le m$:

- $R(u) = \mathop{\rm xor}\limits_{v=1}^{m} {(f(u,v) + u + v)}$ ($\rm xor$ refers to the bitwise XOR operation, corresponding to the `^` operator in C++).

## Input Format

The first line contains a positive integer $m$, representing the number of bowls of noodles.

The next $m$ lines describe each bowl of noodles: the $i$-th line starts with a positive integer $n_i$, indicating the number of noodles in the $i$-th bowl; followed by $n_i$ non-negative integers $A_{i,j}$ describing the widths of the noodles.

## Output Format

Output $m$ lines, each containing an integer, where the $i$-th line's integer is $R(i)$.

## Sample Input and Output

### Input Sample #1

```
3
3 1 2 3
3 3 4 5
2 4 2
```

### Output Sample #1

```
4
7
7
```

## Notes/Hints

### Sample Explanation

For sample 1:

- $\def\x{\operatorname{xor}} R(1) = {(f(1,1)+2)}\x{(f(1,2)+3)}\x{(f(1,3)+4)} = 4\x6\x6 = 4$
- $\def\x{\operatorname{xor}} R(2) = {(f(2,1)+3)}\x{(f(2,2)+4)}\x{(f(2,3)+5)} = 6\x8\x9 = 7$
- $\def\x{\operatorname{xor}} R(3) = {(f(3,1)+4)}\x{(f(3,2)+5)}\x{(f(3,3)+6)} = 6\x9\x8 = 7$

### Data Size and Constraints

For $100\%$ of the data, $m \le 10^4$, $n_i \le 500$, $0 \le A_{i,j} \le 10^9$.

### Notes

This problem is from THUPC (THU Programming Contest, Tsinghua University Programming Contest) 2019.

For solutions and other resources, visit https://github.com/wangyurzee7/THUPC2019.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
