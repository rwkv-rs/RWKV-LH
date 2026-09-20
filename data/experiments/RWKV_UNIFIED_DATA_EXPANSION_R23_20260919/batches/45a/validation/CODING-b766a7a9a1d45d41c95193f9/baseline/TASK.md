There are $N$ single boys and $N$ single girls. The happiness value for boy $i$ and girl $j$ being together is $H_{i,j}$.

A matching is an arrangement of these $N$ boys and girls such that each boy has exactly one girlfriend and each girl has exactly one boyfriend.

The happiness value of a matching is the sum of the happiness values of all $N$ pairs of boy-girl friends.

The classic problem is to calculate the matching with the maximum happiness value, known as the perfect matching. However, perfect matchings are not always unique. You need to calculate the intersection of all perfect matchings.

## Input Format

The first line of the input is a positive integer $N$.

Next is an $N \times N$ matrix $H$, where $H_{i,j}$ represents the happiness value for boy $i$ and girl $j$ being together.

## Output Format

The first line of the output should be the happiness value of the perfect matching. Following this, there should be several lines, each containing a pair of integers $i$ and $j$, indicating that boy $i$ and girl $j$ are in the intersection of all perfect matchings. These pairs should be output in increasing order of $i$.

## Sample Input and Output

### Input Sample #1

```
3
1 1 1
2 1 1
1 1 1
```

### Output Sample #1

```
4
2 1
```

## Notes/Hints

- For $30\%$ of the data, $N \leq 30$;
- For $100\%$ of the data, $1 \leq N \leq 80$, $0 \leq H_{i,j} \leq 5 \times 10^3$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
