Yoshino has given you a sequence of length $n$, where the $i$-th element is $a_i$.

Now, Yoshino will perform $m$ operations on the sequence.

There are two types of operations:

- $1\ l\ r\ x$: Yoshino modifies the elements in the sequence with indices in the range $[l, r]$ to form an arithmetic sequence starting from $x$ with a common difference of $1$.
- $2$: Yoshino queries the number of inversions in the entire sequence. An inversion is defined as a pair $(i, j)$ such that $i < j$ and $a_i > a_j$.

## Input Format

The first line contains two integers $n$ and $m$.

The second line contains $n$ integers, where the $i$-th integer is $a_i$.

The next $m$ lines each represent an operation, as described above.

## Output Format

For each query, output a single integer on a new line representing the answer.

## Sample Input and Output

### Input Sample #1

```
3 3
3 2 1 
2 
1 1 3 1 
2 
```

### Output Sample #1

```
3 
0 
```

## Notes/Hints

**Sample Explanation**

The first operation is a query, and there are three inversions: $(1,3)$, $(2,3)$, and $(1,2)$, so the answer is $3$.

After the second operation, the sequence becomes $1\ 2\ 3$.

The third operation is a query, and there are no inversions in the sequence, so the answer is $0$.

For more samples, please visit [this link](https://www.luogu.com.cn/paste/j4nq14ov).

---

**Data Range**

**This problem uses subtask testing**

| Subtask Number | $n,m\le$       | Special Conditions                     | Score | Time Limit |
| -------------- | -------------- | -------------------------------------- | ----- | ---------- |
| $1$            | $500$          | None                                   | $10$  | $1s$       |
| $2$            | $3\times 10^3$ | None                                   | $10$  | $1s$       |
| $3$            | $3\times 10^4$ | Modification length is $1$             | $15$  | $2s$       |
| $4$            | $3\times 10^4$ | Maximum value in the sequence is $15$  | $20$  | $2s$       |
| $5$            | $3\times 10^4$ | Every odd operation $1$ is $1\ 1\ n\ 1$| $20$  | $2s$       |
| $6$            | $3\times 10^4$ | No special restrictions                | $25$  | $2s$       |

For all data, $1\le n,m,a_i\le 3\times 10^4$, $1\le l\le r\le n$, $1\le x\le 3\times 10^4-r+l$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
