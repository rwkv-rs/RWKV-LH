There is an integer sequence of length $n$, denoted as $a_1, a_2, \cdots, a_n$ (which may contain negative numbers). Now, perform $q$ operations on it, each operation being one of the following two types:

- `0 l r x` indicates that for the interval $[l, r]$, assign $a_i$ to $\max(a_i, x)$;
- `1 l r` asks for the maximum subarray sum in the interval $[l, r]$. That is, $\max(0, \max_{l \le u \le v \le r} (\sum_{i=u}^v a_i))$.

## Input Format

The first line contains two positive integers $n$ and $q$, representing the length of the sequence and the number of operations, respectively.

The second line contains $n$ positive integers $a_1, a_2, \cdots, a_n$, representing the initial sequence.

The next $q$ lines, each in the form of `0 l r x` or `1 l r`, represent an operation.

## Output Format

For each operation in the form of `1 l r`, output a single integer on a new line representing the answer.

## Sample Input and Output

### Input Sample #1

```
5 7
2 -4 6 -5 5
1 1 5
0 1 5 -4
1 1 5
0 3 4 -1
1 1 5
0 1 3 -1
1 1 5
```

### Output Sample #1

```
6
7
10
11
```

## Notes

### Sample Explanation

For Sample #1:

- The first query on the sequence $2, -4, 6, -5, 5$ yields a maximum subarray sum of $6$;
- The second query on the sequence $2, -4, 6, -4, 5$ yields a maximum subarray sum of $7$;
- The third query on the sequence $2, -4, 6, -1, 5$ yields a maximum subarray sum of $10$;
- The fourth query on the sequence $2, -1, 6, -1, 5$ yields a maximum subarray sum of $11$.

### Data Size and Constraints

For all data, $1 \le n \le 10^5, 1 \le q \le 2 \times 10^5, |a_i|, |x| \le 10^9$.

- For $10\%$ of the data, $n, q \le 200$;
- For another $10\%$ of the data, $n, q \le 2000$;
- For another $25\%$ of the data, each operation of type `0` satisfies $l = r$ (i.e., only point modifications);
- For another $20\%$ of the data, each operation of type `1` satisfies $l = 1, r = n$ (i.e., only global queries);
- For the remaining $35\%$ of the data, there are no special constraints.

**There are 3 hack data points provided by the problem setter.**

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
