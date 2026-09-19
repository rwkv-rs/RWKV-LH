Given a positive integer, an operation is defined as selecting $l, r$, and removing all digits from the $l\sim r$ positions counting from the end, then forming a new positive integer with the remaining digits. For example, removing the $2\sim 3$ digits from the end of $123456$ results in $1236$.

There are $T$ queries, each providing a positive integer $n$, and you need to answer whether this integer can be transformed into a multiple of $4$ through **at most one operation** (including no operation).

Note that you cannot remove all digits.

## Input Format

The input consists of $T+1$ lines.

The first line contains a positive integer $T$.

The next $T$ lines each contain a positive integer $n$. It is guaranteed that $n$ does not have leading zeros.

## Output Format

The output consists of $T$ lines.

For each of the $T$ sets of data, output one line indicating the answer to the problem. If it is possible, output `Yes`; if not, output `No`.

## Sample Input and Output

### Sample Input #1

```
3
234
1
286
```

### Sample Output #1

```
Yes
No
Yes
```

### Sample Input #2

```
1
2386
```

### Sample Output #2

```
Yes
```

## Notes

### Sample 1 Explanation

For the first set of data: Removing the $2\sim 3$ digits from the end results in $4$, which is a multiple of $4$.

For the second set of data: It can be proven that no solution exists.

For the third set of data: Removing the $1$ digit from the end results in $28$, which is a multiple of $4$.

### Data Range

For the first $10\%$ of the data, $1 \le n \le 9$.
For the first $30\%$ of the data, $1 \le T \le 10, 1 \le n \le 100$.
For an additional $10\%$ of the data, $T = 1$.
For the first $60\%$ of the data, $1 \le T \le 10, 1 \le n \le 10^9$.
For $100\%$ of the data, $1 \le T \le 10^2, 1 \le n \le 10^{18}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
