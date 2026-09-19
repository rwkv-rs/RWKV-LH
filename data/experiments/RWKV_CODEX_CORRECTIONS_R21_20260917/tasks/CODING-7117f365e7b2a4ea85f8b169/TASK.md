Given a sequence \( a \) of length \( n \) with indices from 1 to \( n \), there are \( m \) query operations. Each query provides an interval \([l, r]\) and asks for a subinterval \([l', r']\) such that \( l \le l' \le r' \le r \), the number of distinct values in \([l', r']\) is less than the number of distinct values in \([l, r]\), and the length of \([l', r']\) (i.e., \( r' - l' + 1 \)) is maximized. If no such subinterval exists, output \( 0 \).

## Input Format

The first line contains two numbers \( n \) and \( m \).

The next line contains \( n \) numbers representing the elements of the sequence \( a \).

The following \( m \) lines each contain two numbers \( l \) and \( r \) representing a query. Output the length of the subinterval, i.e., \( r' - l' + 1 \).

## Output Format

For each query, output a single number representing the answer.

## Sample Input and Output

### Input Sample #1

```
5 4
1 3 2 3 4
2 4
1 3
2 5
1 1
```

### Output Sample #1

```
1
2
3
0
```

## Notes/Hints

Idea: ccz181078, Solution: ccz181078, Code: ccz181078, Data: ccz181078

For 20% of the data, \( n, m \le 100 \).

For 40% of the data, \( n, m \le 1000 \).

For an additional 20% of the data, \( a_i \le 10 \).

For 100% of the data, \( 1 \le n, m, a_i \le 2 \times 10^6 \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
