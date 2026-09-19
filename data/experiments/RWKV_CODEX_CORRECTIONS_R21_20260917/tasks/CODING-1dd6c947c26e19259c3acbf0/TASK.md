A permutation of length $ N $ is a rearrangement of $ N $ integers $ (1, 2, ..., N) $.

For a permutation $ A $ of length $ N $, the inversion number of $ A $ is the number of pairs $ (i, j) $ ($ 1 \leq i < j \leq N $) such that $ A_i > A_j $.

Find the number of permutations of length $ N $ such that the remainder when the inversion number is divided by $ K $ is $ m $, modulo $ 10^9+7 $.

## Input Format

> $ N $ $ K $ $ m $

## Output Format

Output the number of permutations of length $ N $ such that the remainder when the inversion number is divided by $ K $ is $ m $, modulo $ 10^9+7 $.

## Sample Input and Output

### Sample Input #1

```
3 10 2
```

### Sample Output #1

```
2
```

### Sample Input #2

```
7 9 1
```

### Sample Output #2

```
599
```

### Sample Input #3

```
100 1 0
```

### Sample Output #3

```
437918130
```

## Notes/Hints

### Constraints

- $ 1 \leq N \leq 10^{18} $
- $ 0 \leq m < K \leq 10 $

### Sample Explanation 1

The inversion number of a permutation of length $ 3 $ is at most $ 3 $, so in this case, we count the permutations with an inversion number of $ 2 $. The permutations with an inversion number of $ 2 $ are $ (3, 1, 2) $ and $ (2, 3, 1) $, which are $ 2 $ in total.

### Sample Explanation 3

Output the result modulo $ 10^9+7 $.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
