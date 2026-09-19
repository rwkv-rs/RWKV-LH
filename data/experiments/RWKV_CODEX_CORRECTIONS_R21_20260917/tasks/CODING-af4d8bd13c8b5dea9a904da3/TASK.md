"Finally... it's time to say goodbye."

"After this, we may never meet again..."

"No matter what, it's time to part..."

"I understand. Thank you for being by my side these days."

"I feel the same. If possible, I wish I could continue to be by your side."

"After parting, I won't be the same as I am now..."

"At least not like this."

"After leaving you, I won't be the same either..."

"Where are you going? Where do you want to go? Don't leave, don't leave! If you must go, take me with you!"

...

"So... what should we do now?"

"Let's just enjoy the dance and music!"

The sound of violin and accordion echoes, so familiar yet so strange...

## Problem Description

Before parting, Xiao M left a note for Xiao K—

If you can complete his task, I might meet you again.

Given an **infinite** matrix $A$ where $A_{i,j} = ij \gcd(i,j)$.

There are $m$ operations, each line containing 1 to 3 integers, with the following meanings:

$1$: Perform Gaussian elimination on matrix $A$ to make it an upper triangular matrix.

**Note**: Here, Gaussian elimination only allows adding a multiple of one row to another row, without swapping any rows or multiplying a row by a factor. It is guaranteed that the resulting matrix will still be an upper triangular matrix, and all elements in the matrix after elimination will be non-negative integers.

$2\ x\ y$: Find the value of $A_{x,y}$ in the current matrix.

$3\ x$: Find the sum $\sum_{i=1}^{x}\sum_{j=1}^{x}A_{i,j}$.

$4\ x$: Let $B$ be an $x$-order matrix where $B_{i,j} = A_{i,j}$. You need to find the determinant of $B$.

**All answers should be modulo $998244353$.**

If you are unfamiliar with determinants, please refer to [this link](https://oi-wiki.org/math/gauss/#_12), where $\text{det}$ denotes the determinant of a matrix.

~~After completing Xiao M's task for Xiao K, you can check out the sheet music for violin and accordion.~~

## Input Format

The first line contains an integer $m$.

The next $m$ lines, each containing 1 to 3 integers, represent the operations.

## Output Format

Several lines, each showing the answer modulo $998244353$.

## Sample Input and Output

### Sample Input #1

```
6
4 4
2 4 4
3 4
1
2 4 4
3 4
```

### Sample Output #1

```
2304
64
186
32
72
```

## Notes/Hints

[Sample Input 1](https://www.luogu.com.cn/paste/p2w7kxik) [Sample Output 1](https://www.luogu.com.cn/paste/2tqpm5zj)

[Sample Input 2](https://www.luogu.com.cn/paste/u20duxjv) [Sample Output 2](https://www.luogu.com.cn/paste/jcn7ohaw)

### Sample Explanation

Note that the ranges of $x$ and $y$ in the queries are no greater than 4, so we consider the $4 \times 4$ submatrix in the upper left corner of $A$ for explanation. It is easy to prove that this will not affect the results.

Before Gaussian elimination, the matrix is $\begin{pmatrix}1&2&3&4\\2&8&6&16\\3&6&27&12\\4&16&12&64\end{pmatrix}$, and after Gaussian elimination, it becomes $\begin{pmatrix}1&2&3&4\\0&4&0&8\\0&0&18&0\\0&0&0&32\end{pmatrix}$.

### Data Range

| Subtask Number | Does Operation $1$ Exist | $x, y \leq$ Before Operation $1$ | $x, y \leq$ After Operation $1$ | $x \leq$ Before Operation $3$ | $x \leq$ After Operation $3$ | $x \leq$ in Operation $4$ | Score |
| :------------: | :---------------------: | :-----------------------------: | :-----------------------------: | :--------------------------: | :-------------------------: | :----------------------: | :---: |
| Subtask 1      | No                      | $5000$                          | N/A                             | $500$                        | N/A                         | N/A                      | $4$   |
| Subtask 2      | No                      | $10^{18}$                       | N/A                             | $500$                        | N/A                         | N/A                      | $13$  |
| Subtask 3      | No                      | $10^{18}$                       | N/A                             | $5 \times 10^6$              | N/A                         | $50$                     | $15$  |
| Subtask 4      | No                      | $10^{18}$                       | N/A                             | $10^8$                       | N/A                         | $100$                    | $16$  |
| Subtask 5      | Yes                     | $10^{18}$                       | $100$                           | $5 \times 10^6$              | $100$                       | N/A                      | $17$  |
| Subtask 6      | Yes                     | $10^{18}$                       | $5 \times 10^5$                 | $10^8$                       | $10^3$                      | $100$                    | $17$  |
| Subtask 7      | Yes                     | $10^{18}$                       | $5 \times 10^6$                 | $10^8$                       | $5 \times 10^6$             | $5 \times 10^6$          | $18$  |

For $100\%$ of the data, $1 \leq m \leq 10^5$, and the sum of $x$ in all Operation $3$ before Operation $1$ does not exceed 10 times the $x$ range of each test point.

It is guaranteed that Operation $1$ appears no more than once.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
