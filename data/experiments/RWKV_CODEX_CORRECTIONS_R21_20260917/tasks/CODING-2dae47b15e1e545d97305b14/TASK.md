$\color{gray}\text{zrmpaul}$ has an array consisting of $n$ integers: $a_1,a_2,...,a_n$. The initial value of $a_i$ is $i(1\le i\le n)$. There are $m$ operations, including four types as follows.

- Type `1`: Sort the array in ascending order.
- Type `2`: Sort the array in ascending order and then reverse it (i.e., sort in descending order).
- Type `3 x y`: Swap $a_x$ and $a_y$. It is guaranteed that $x$ is not equal to $y$, and $1\leq x, y \leq n$.
- Type `4`: Reverse the array.

You need to output the array after $m$ operations.

## Input Format

The first line contains two integers $n, m (1\leq n, m\leq 10^6)$, representing the length of the sequence and the number of operations, respectively.

The next $m$ lines describe the operations. Each line corresponds to one operation.

## Output Format

Output one line containing $n$ integers, representing the sequence after all operations.

## Sample Input and Output

### Input Sample #1

```
5 5
1
2
3 2 4
4
3 1 5
```

### Output Sample #1

```
5 4 3 2 1
```

## Notes/Hints

**[This problem uses batched testing]**

- Subtask 1 (24 points): $1\leq n, m\leq 2 \times 10^3$.
- Subtask 2 (13 points): There are no Type 3 operations.
- Subtask 3 (63 points): $1\leq n, m\leq 10^6$.

**Sample Explanation**

The sequence undergoes the following operations:
> $1, 2, 3, 4, 5$     
$1, 2, 3, 4, 5$   
$5, 4, 3, 2, 1$   
$5, 2, 3, 4, 1$   
$1, 4, 3, 2, 5$   
$5, 4, 3, 2, 1$

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
