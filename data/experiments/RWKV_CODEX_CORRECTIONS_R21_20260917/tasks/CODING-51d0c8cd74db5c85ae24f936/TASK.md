Given an integer sequence $ A=(A_1,A_2,\cdots,A_N) $ of length $ N $ consisting of $ 0 $ and $ 1 $.

Currently, a piece is located at the point $ (0,0) $ on a two-dimensional plane. You can repeat the following operation any number of times:

- Choose integers $ x,y $ ($ 1 \leq x,y \leq N $), and increase the $ X $ and $ Y $ coordinates of the piece by $ x $ and $ y $ respectively. However, the following two conditions must be satisfied:
  - $ A_x=1 $ holds.
  - Let the coordinates of the piece after the operation be $ (p,q) $, then $ q \leq p $ must hold.

Find the number of ways to move the piece to the coordinate $ (N,N) $ modulo $ 998244353 $.

## Input Format

The input is given from the standard input in the following format:

> $ N $ $ A_1 $ $ A_2 $ $ \cdots $ $ A_N $

## Output Format

Output the answer.

## Sample Input and Output

### Sample Input #1

```
2
1 1
```

### Sample Output #1

```
2
```

### Sample Input #2

```
1
0
```

### Sample Output #2

```
0
```

### Sample Input #3

```
4
1 1 0 1
```

### Sample Output #3

```
10
```

### Sample Input #4

```
25
1 0 1 1 0 0 0 0 1 0 0 1 0 1 1 1 0 0 1 0 0 0 1 0 0
```

### Sample Output #4

```
934946952
```

## Notes/Hints

### Constraints

- $ 1 \leq N \leq 2 \times 10^5 $
- $ A_i \in \{0,1\} $

### Sample Explanation 1

The following two ways to move the piece are considered:
- $ (0,0) \rightarrow (1,1) \rightarrow (2,2) $
- $ (0,0) \rightarrow (2,2) $

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
