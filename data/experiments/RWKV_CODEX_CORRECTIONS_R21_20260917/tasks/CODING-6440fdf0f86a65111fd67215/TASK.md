Last time, NaCly\_Fish wanted to teach her juniors about linear homogeneous recurrence with constant coefficients, but due to her limited intelligence and shallow knowledge, she was repeatedly outsmarted by her classmates in the computer room.

Later, she heard about polynomial recurrence and went to consult Captain China, $\mathsf E \color{red}\mathsf{ntropyIncreaser}$. However, $\mathsf E \color{red}\mathsf{ntropyIncreaser}$ found it too simple and only responded with, "Haven't you read the candidate team papers?"

NaCly\_Fish finally got the papers but couldn't understand them at all. So, she turned to you, who is both strong and enthusiastic, to help her with this problem.

## Problem Description

For an infinite sequence $a$, it is known that for all $n \ge m$, the following holds:
$$\sum_{k=0}^m a_{n-k} P_k(n) = 0$$
where $P_k$ are polynomials of degree no more than $d$.  
Given the coefficients of all $P_k$ and $\{ a_i \}_{i=0}^{m-1} $, find $a_n$.

Since the answer may be very large, it should be taken modulo $998244353$.

## Input Format

The first line contains three positive integers $n, m, d$.  
The second line contains $m$ non-negative integers, representing $\{ a_i \}_{i=0}^{m-1} $.  
The next $m+1$ lines, each containing $d+1$ non-negative integers, give the coefficients of $P_k$ from low to high in the $(k+3)$-th line.

## Output Format

Output a single integer on one line, representing the answer.

## Sample Input and Output

### Sample Input #1

```
5 2 1
1 0
998244352 0
998244352 1
998244352 1
```

### Sample Output #1

```
44
```

### Sample Input #2

```
233 2 3
1 0
998244352 0 0 0
0 998244349 4 0
0 8 998244337 8
```

### Sample Output #2

```
193416411
```

### Sample Input #3

```
114514 7 7
1 9 8 2 6 4 7
9 1 8 2 7 6 5 3
2 8 4 6 2 9 4 5
1 9 2 6 0 8 1 7
1 9 1 9 8 1 0 7
1 1 4 5 1 4 4 4
4 4 4 4 4 4 4 4
9 9 8 2 4 4 3 5
1 9 8 6 0 6 0 4
```

### Sample Output #3

```
565704112
```

## Notes

### Sample Explanation #1

The recurrence here is $a_n \equiv (n-1)(a_{n-1}+a_{n-2}) \pmod{998244353}$, and it's easy to calculate that $a_5 \equiv 44 \pmod{998244353}$.

### Data Range

For $30\%$ of the data, $1 \le n \le 10^6$.  
For $100\%$ of the data, $1 \le m, d \le 7$, $1 \le n \le 6 \times 10^8$.

All inputs are no more than $6 \times 10^8$.  
For all $x \in [m, n] \cap \mathbb Z$ such that $P_0(x) \not \equiv 0 \pmod{998244353}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
