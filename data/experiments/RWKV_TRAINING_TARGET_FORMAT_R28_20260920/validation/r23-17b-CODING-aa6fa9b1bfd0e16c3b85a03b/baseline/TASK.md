Imagine you are an air traffic controller. Each airplane has a safe landing time window. Your instructions must comply with each airplane's time window. Additionally, the landing times should be as evenly spaced as possible to maximize the smallest interval between consecutive landings. For example, if three airplanes land at 10:00 am, 10:05 am, and 10:15 am, then the smallest interval is five minutes between the first two airplanes. Not all intervals need to be the same, but the smallest interval should be as large as possible.

## Input Format

The input consists of multiple datasets. The first line of each dataset contains an integer $n$ $(2 ≤ n ≤ 8)$, representing the number of airplanes. The next $n$ lines each contain two integers $a_i$ and $b_i$, denoting the time window $[a_i, b_i]$ during which the airplane can land. The times $a_i$ and $b_i$ are expressed in minutes and satisfy $0 ≤ a_i ≤ b_i ≤ 1440$. The last line of input is a zero.

## Output Format

For each dataset, print which dataset it is, followed by the largest possible smallest interval, with the unit in minutes and seconds, rounded to the nearest integer (round half up). The format should match the example.

## Input and Output Example

### Sample Input

```
3
0 10
5 15
10 15
2
0 10
10 20
0
```

### Sample Output

```
Case 1: 7:30
Case 2: 20:00
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
