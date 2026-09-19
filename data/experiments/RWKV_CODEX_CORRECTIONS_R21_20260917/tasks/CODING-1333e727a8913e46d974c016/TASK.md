Farmer John is distributing haybales on his farm.

Farmer John's farm has \( N \) (\( 1 \le N \le 2 \cdot 10^5 \)) barns located at integer points \( x_1, \ldots, x_N \) (\( 0 \le x_i \le 10^6 \)) on a number line. Farmer John plans to transport \( N \) haybales to an integer point \( y \) (\( 0 \le y \le 10^6 \)) and then deliver one haybale to each barn.

Unfortunately, Farmer John's transportation system wastes a lot of haybales. Specifically, given some \( a_i, b_i \) (\( 1 \le a_i, b_i \le 10^6 \)), each haybale moved one unit to the left wastes \( a_i \) haybales; each haybale moved one unit to the right wastes \( b_i \) haybales. Formally, the number of wasted haybales when a haybale moves from point \( y \) to a barn at \( x \) is:

\[
\begin{cases}
a_i \cdot (y - x) & \text{if } y > x \\
b_i \cdot (x - y) & \text{if } x > y
\end{cases}
\]

Given \( Q \) (\( 1 \le Q \le 2 \cdot 10^5 \)) independent queries, each providing a set of \( (a_i, b_i) \) values, help Farmer John calculate the minimum number of haybales wasted when choosing \( y \) optimally.

## Input Format

The first line contains \( N \).

The next line contains \( x_1 \ldots x_N \).

The next line contains \( Q \).

The next \( Q \) lines each contain two integers \( a_i, b_i \).

## Output Format

Output \( Q \) lines, the \( i \)-th line containing the answer for the \( i \)-th query.

## Sample Input and Output

### Input Sample #1

```
5
1 4 2 3 10
4
1 1
2 1
1 2
1 4
```

### Output Sample #1

```
11
13
18
30
```

## Notes

### Sample Explanation 1

For the second query in the sample, the optimal choice is \( y = 2 \), and the number of wasted haybales is \( 2(2-1) + 2(2-2) + 1(3-2) + 1(4-2) + 1(10-2) = 1 + 0 + 1 + 2 + 8 = 13 \).

### Test Case Properties

- Test case 2 satisfies \( N, Q \le 10 \).
- Test case 3 satisfies \( N, Q \le 500 \).
- Test cases 4-6 satisfy \( N, Q \le 5000 \).
- Test cases 7-16 have no additional restrictions.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
