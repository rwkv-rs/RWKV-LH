Takahashi and Aoki are playing a two-player game as follows:

First, a positive integer $ N $ is given. Also, a variable $ x $ is initialized to $ 1 $. Starting from Takahashi, Takahashi and Aoki take turns performing the following operation:

- Replace the value of $ x $ with $ 2x $ or $ 2x+1 $.

When $ x $ becomes greater than $ N $, the person who performed the last operation loses.

Determine which player wins when both play optimally.

## Input Format

The input is given from the standard input in the following format:

> $ N $

- The first line contains a positive integer $ N $ ($ 1≦N≦10^{18} $).

## Output Format

Output `Takahashi` if Takahashi wins, or `Aoki` if Aoki wins, on a single line. End the output with a newline.

## Sample Input and Output

### Sample Input #1

```
1
```

### Sample Output #1

```
Aoki
```

### Sample Input #2

```
5
```

### Sample Output #2

```
Takahashi
```

### Sample Input #3

```
7
```

### Sample Output #3

```
Aoki
```

### Sample Input #4

```
10
```

### Sample Output #4

```
Takahashi
```

### Sample Input #5

```
123456789123456789
```

### Sample Output #5

```
Aoki
```

## Notes/Hints

### Sample Explanation 1

No matter what operation Takahashi performs, $ x > 1 $.

### Sample Explanation 2

If Takahashi sets $ x = 3 $, no matter what operation Aoki performs, $ x > 5 $.

### Sample Explanation 5

$ N $ does not fit into a 32-bit integer type.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
