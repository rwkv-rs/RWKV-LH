## Problem Description

**Note: For convenience, all strings start at position $1$, i.e., they are numbered from $1$.**

Xiao L considers the original text before grassing and the result after grassing as two strings $A$ and $B$ **consisting only of lowercase letters**.

We define "split sequence" and "split string" as follows:

- For a string of length $n$, a "split sequence" is defined as: there exists a sequence $p$ of length $k+2$ such that $0=p_0<p_1<p_2<...<p_k<p_{k+1}=n+1$. For a "split sequence", its "split string" is the substring from $p_i+1$ to $p_{i+1}-1$ (for $i \in[0,k]$) (which can be an empty string). Obviously, for a split sequence of length $k+2$, there are $k+1$ split strings.

- Two split sequences ($p$ and $q$) for the same string are different **if and only if** the lengths of the sequences are different ($k_1 \neq k_2$), or **there exists an $i$ such that $p_i \neq q_i$**.

Different people have different ways of understanding the same original text and result. We define a way of understanding as follows:

- For strings $A$ and $B$, we find a split sequence for each of these strings ($p$ and $q$), which satisfy the following requirements:
  1. The lengths of the two split sequences are equal ($k_1 = k_2$).
  1. For any $i$, $A[p_i] = B[q_i]$, i.e., **the character at the $p_i$-th position in $A$ is the same as the character at the $q_i$-th position in $B$**.

- The "grass level" of this understanding method is defined as **the sum of the $t$-th powers of the lengths of all split strings** in both strings, i.e., $\sum\limits_{i=0}^{k_1}(p_{i+1}-p_i-1)^t + \sum\limits_{i=0}^{k_2}(q_{i+1}-q_i-1)^t$.

- Two understanding methods are different **if and only if** the $p$ of the two methods are different, or the $q$ of the two methods are different.

Xiao L wants to know the sum of the grass levels of all understanding methods. Since he (also) dislikes the number $998244353$, he does not want you to tell him the result that is this number, so you need to take the result modulo $998244353$.

## Input Format

The first line contains three positive integers $n, m, t$.

The next line contains a string of length $n$, representing string $A$.

The next line contains a string of length $m$, representing string $B$.

## Output Format

One line, an integer representing the result modulo $998244353$.

## Sample Input and Output

### Sample Input #1

```
3 4 2
abc
bacb
```

### Sample Output #1

```
74
```

### Sample Input #2

```
7 8 5
ccbbacb
bbbdadba
```

### Sample Output #2

```
337322
```

### Sample Input #3

```
3 4 1000000
abc
bacb
```

### Sample Output #3

```
424285944
```

## Notes

For the first sample, there are the following understanding methods:
+ $p=\{0,4\}, q=\{0,5\}$, grass level is $25$.
+ $p=\{0,1,4\}, q=\{0,2,5\}$, grass level is $9$.
+ $p=\{0,2,4\}, q=\{0,1,5\}$, grass level is $11$.
+ $p=\{0,2,4\}, q=\{0,4,5\}$, grass level is $11$.
+ $p=\{0,3,4\}, q=\{0,3,5\}$, grass level is $9$.
+ $p=\{0,1,2,4\}, q=\{0,2,4,5\}$, grass level is $3$.
+ $p=\{0,1,3,4\}, q=\{0,2,3,5\}$, grass level is $3$.
+ $p=\{0,2,3,4\}, q=\{0,1,3,5\}$, grass level is $3$.

The total grass level is $74$.

### Data Range

"This problem uses bundled testing"

- Subtask 1 ($20\%$): $n, m \leq 50, t \leq 2$.
- Subtask 2 ($30\%$): $n, m \leq 200, t \leq 2$.
- Subtask 3 ($20\%$): $t \leq 10$.
- Subtask 4 ($30\%$): No special restrictions.

For $100\%$ of the data, $n, m \leq 1000, t \leq 1000000$, and $A$ and $B$ **contain only lowercase letters**.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
