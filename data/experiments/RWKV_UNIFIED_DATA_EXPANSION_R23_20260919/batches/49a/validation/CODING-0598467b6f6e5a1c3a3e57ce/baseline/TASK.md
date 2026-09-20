Little M's laboratory has many power strips. These power strips are numbered from $1$ to $n$ and are arranged from left to right in a row.

Every morning, all the power strips are unused. Whenever a student arrives at the lab, they plug their laptop's power cord into an unused power strip.

The students in the lab are peculiar; they follow this process: first, they find the longest interval of unused power strips.

If there are multiple intervals of the same length, they choose the one that is furthest to the right. Then, they plug their power cord into the middle of this interval.

If the interval length is even, they still choose the one that is further to the right. When a student leaves the lab, they unplug their power cord.

The data guarantees that every student arrives at the lab with at least one empty power strip available.

You need to calculate how many power strips in the interval $[l, r]$ have been used.

## Input Format

The first line contains two integers $n$ and $q$, representing the number of power strips and the number of queries, respectively.

The next $q$ lines each start with an integer $k$.

- If $k$ is $0$, the next two integers are $l$ and $r$, representing a query.
- Otherwise, $k$ indicates the arrival or departure of a student with the ID $k$. An odd occurrence of $k$ indicates arrival, and an even occurrence indicates departure. Each student's ID is unique.

## Output Format

For each query, output a single integer representing the number of used power strips in the queried interval.

## Sample Input and Output

### Input Sample #1

```
7 10
1
2
3
0 1 2
0 4 7
0 2 5
20
0 6 6
99
0 4 6
```

### Output Sample #1

```
1
2
2
1
3
```

## Notes

### Data Size and Constraints

For $30\%$ of the data, $n \le 10^5, q \le 10^3$;

For $100\%$ of the data, $1 \le n \le 10^9, 1 \le q \le 10^5, 0 \le k \le 10^9, 1 \le l \le r \le n$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
