Along the highway, there are $n$ villages. The highway is represented as an integer axis, and each village is identified by a single integer coordinate. The distance between two positions is the absolute value of the difference in their integer coordinates.

Now, $m$ post offices are to be established. These post offices will be built in some, but not necessarily all, of the villages. To establish the post offices, the locations for their construction should be chosen such that the sum of the distances from each village to its nearest post office is minimized.

You are to write a program that, given the positions of the villages and the number of post offices, calculates the minimum possible total sum of distances from each village to its nearest post office.

## Input Format

The first line contains two integers, representing the number of villages $n$ and the number of post offices $m$, respectively.

The second line contains $n$ integers, where the $i$-th integer represents the coordinate $a_i$ of the $i$-th village.

## Output Format

Output a single integer representing the answer.

## Sample Input and Output

### Input Sample #1

```
5 2
0 1 2 3 4
```

### Output Sample #1

```
3
```

## Notes

### Data Size and Constraints

This problem consists of five test cases, each with the following information:

| Test Case Number | $n = $ | $a_i \leq $ |
| :--------------: | :----: | :---------: |
| 1 | $50000$ | $6 \times 10^4$ |
| 2 | $150000$ | $2 \times 10^5$ |
| 3 | $299998$ | $5 \times 10^5$ |
| 4 | $499998$ | $10^6$ |
| 5 | $499999$ | $2\times 10^6$ |

For all test cases, it is guaranteed that $1 \leq m \leq n \leq 5 \times 10^5$, $0 \leq a_i \leq 2\times 10^6$, and the values of $a_i$ are uniformly random within the specified range.

The final answer is guaranteed to be no more than $10^9$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
