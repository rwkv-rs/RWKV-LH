The post office has recently released a set of commemorative stamps. This set contains $N$ stamps, each with a unique face value, numbered sequentially from $1$ cent, $2$ cent, ..., to $N$ cent.

Xiao Ming is a philatelist who loves this set of stamps. Unfortunately, he only has $M$ cents and cannot afford the entire set. However, he wishes to spend all his money exactly. As a philatelist, Xiao Ming does not want to buy stamps with discontinuous numbers. Therefore, he plans to buy a continuous sequence of stamps from $a$ cent to $b$ cent, totaling $b-a+1$ stamps, with the total value exactly $M$ cents.

Your task is to find all valid schemes and output them in the form $\left[a,b\right]$.

## Input Format

The input file contains a single line with two integers $N$ and $M$ ($1 \le N, M \le 10^9$), separated by a space.

## Output Format

The output file should contain each valid scheme on a new line: $\left[a,b\right]$, sorted by the value of $a$ in ascending order.

## Sample Input and Output

### Sample Input #1

```
20 15
```

### Sample Output #1

```
[1,5]
[4,6]
[7,8]
[15,15]
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
