You are playing a game called Tenkaichi Calculation. Tenkaichi Calculation is defined as follows:

- Given integers $ M $ and $ N $ where $ 1 \leq M \leq 10^5 $ and $ 1 \leq N \leq 10^5 $, and an array $ A $ of $ N $ integers where each integer is between $ 0 $ and $ M-1 $.
- Perform the operation of multiplying all elements of the array by $ 10 $ multiple times.
- Then, perform the operation of adding $ 1 $ to a single element of the array multiple times.
- The game is cleared when all elements of the array become multiples of $ M $.

For example, when $ M = 7 $, $ N = 4 $, and $ A = [0, 1, 2, 3] $, if you multiply all elements by $ 10 $ three times, then add $ 1 $ to the second element once, add $ 1 $ to the third element twice, and add $ 1 $ to the fourth element three times, $ A = [0, 1001, 2002, 3003] $, and all elements become multiples of $ M $ with a total of $ 9 $ operations.

Calculate the total number of operations required to clear the Tenkaichi Calculation with the fewest operations possible.

## Input Format

The input is given from the standard input in the following format:

> $ M $ $ N $ $ A_1 $ $ A_2 $ : $ A_N $

- The first line contains two integers $ M\ (1 \leq M \leq 10^5) $ and $ N\ (1 \leq N \leq 10^5) $ separated by a space.
- The next $ N $ lines contain the elements of array $ A $ where each $ A_i\ (0 \leq A_i < M) $ is given.

## Output Format

Output the total number of operations required to clear the Tenkaichi Calculation with the fewest operations possible. End the output with a newline.

## Sample Input and Output

### Sample Input #1

```
7 4
0
1
2
3
```

### Sample Output #1

```
9
```

### Sample Input #2

```
1001 1
1
```

### Sample Output #2

```
4
```

### Sample Input #3

```
1 2
0
0
```

### Sample Output #3

```
0
```

### Sample Input #4

```
12345 5
12
34
56
78
90
```

### Sample Output #4

```
1884
```

## Notes/Hints

### Scoring

There is no partial credit for this problem. If you solve it correctly, you will be awarded $ 130 $ points.

### Sample Explanation 1

This is the case explained in the problem statement.

### Sample Explanation 2

After multiplying by $ 10 $ three times and adding $ 1 $ once, it becomes a multiple of $ M $.

### Sample Explanation 3

All elements are already multiples of $ M $ from the beginning.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
