$ P $ is a prime number $ 299993 $. You are given $ N $ lattice points on the $ xy $ plane. The coordinates of the $ i $-th lattice point are $ (x_i, y_i) $. For a lattice point $ S $ on the plane with coordinates $ (S_x, S_y) $, define the integer $ f(S) $ as follows:

 $ f(S)=\displaystyle\ \prod_{1\leq\ i\leq\ N}\left((S_x\ -\ x_i)^2\ +\ (S_y\ -\ y_i)^2\ \right) $ 

Given an integer $ Z $, find the number of lattice points $ U $ with both $ x $ and $ y $ coordinates between $ 0 $ and $ P-1 $ (inclusive) such that $ f(U)\equiv\ Z\ \pmod\ P $.

## Input Format

The input is given from the standard input in the following format:

> $ N $ $ Z $ $ x_1 $ $ y_1 $ $ x_2 $ $ y_2 $ $ \vdots $ $ x_N $ $ y_N $

## Output Format

Output the answer in one line.

## Sample Input and Output

### Sample Input #1

```
1 1
1 1
```

### Sample Output #1

```
299992
```

### Sample Input #2

```
10 89872
223484 90627
277624 145685
121818 45893
100399 298120
290298 53417
83968 217141
293596 75934
66042 121754
12383 235338
8014 175352
```

### Sample Output #2

```
300588
```

## Notes/Hints

### Constraints

- All inputs are integers.
- $ 1\ \leq\ N\ \leq\ 100 $
- $ 0\ \leq\ Z\ \lt\ P\ =\ 299993 $
- $ 0\ \leq\ x_i\ ,y_i\ \lt\ P\ =\ 299993 $
- $ (x_i, y_i)\neq(x_j, y_j) $ for $ i\neq\ j $

### Sample Explanation 1

For example, when $ S\ =\ (12345,6789) $, $ f(S)\ =\ (12345\ -\ 1)^2\ +\ (6789\ -\ 1)^2\ =\ 152374336\ +\ 46076944\ =\ 198451280 $. There are $ 299992 $ points $ S $ such that $ f(S)\ \equiv\ 1\ \pmod\ P $.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
