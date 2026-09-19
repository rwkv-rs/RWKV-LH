Given a sequence \( A_1, A_2, \ldots, A_N \) and \( Q \) queries \( (L_i, R_i) \), determine whether the elements \( A_{L_i}, A_{L_i+1}, \ldots, A_{R_i} \) are all distinct.

## Input Format

The first line contains two integers \( N \) and \( Q \).  
The second line contains \( N \) integers \( A_1, A_2, \ldots, A_N \).  
The next \( Q \) lines each contain two integers \( L_i \) and \( R_i \).

## Output Format

For each query, output one line containing either `Yes` or `No`.

## Sample Input and Output

### Input Sample #1

```
4 2
1 2 3 2
1 3
2 4
```

### Output Sample #1

```
Yes
No
```

## Notes

For 50% of the test cases, \( N, Q \le 10^3 \).  
For 100% of the test cases, \( 1 \le N, Q \le 10^5 \), \( 1 \le A_i \le N \), \( 1 \le L_i \le R_i \le N \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
