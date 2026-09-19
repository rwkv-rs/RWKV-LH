Given an $N \times M$ integer matrix $\{A[i,j]\}$ ($1 \le i \le N$, $1 \le j \le M$). You are required to answer $K$ queries. Each query $i$ asks for the count of 2D inversions $(x_1, y_1, x_2, y_2)$ that satisfy the following conditions:

- $u_{i,1} \le x_1 \le x_2 \le u_{i,2}$
- and $v_{i,1} \le y_1 \le y_2 \le v_{i,2}$
- and $A[x_1, y_1] > A[x_2, y_2]$

## Input Format

This problem is a submit-answer problem. The input files are `rev1.in` to `rev10.in`.

The first line of the input file `rev*.in` contains three positive integers $N, M, K$.

The next $N$ lines each contain $M$ numbers representing the integer matrix $A$, where the $i$-th row and $j$-th column is $A[i,j]$. The following $K$ lines each contain four integers representing the queries, where the $i$-th line is $u_{i,1}, v_{i,1}, u_{i,2}, v_{i,2}$.

## Output Format

The output file `rev*.out` contains $K$ lines. The $i$-th line is an integer representing the answer to the $i$-th query, which is the count of 2D inversions that satisfy the given conditions.

## Notes

### Scoring Criteria

For each test case, if your output matches the standard output exactly, you will get 10 points; otherwise, you will get 0 points.

**Due to the limitations of the Luogu judge system, please output the XOR sum of all answers. The sample is only for understanding the problem, not for the final output format.**

## Sample Input and Output

### Input Sample #1

```
3 5 3
1 2 3 4 5
9 9 9 9 9
1 4 3 5 2
1 1 2 5
3 1 3 5
2 1 3 5
```

### Output Sample #1

```
0
4
19
```

## Notes

Please ensure to keep the input files `*.in` and your output `*.out` safely backed up to avoid accidental deletion.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
