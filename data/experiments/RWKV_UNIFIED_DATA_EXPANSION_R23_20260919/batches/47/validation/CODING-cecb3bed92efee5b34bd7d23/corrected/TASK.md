The digital root of a number is defined as follows: sum the digits of the number, and repeat this process until the sum is less than 10. For example, the digital root of 64357 is 7, because 6 + 4 + 3 + 5 + 7 = 25, and 2 + 5 = 7. The digital root of a range is defined as the digital root of the sum of all numbers in that range.

Given a sequence A1, A2, A3, ..., An, you are required to answer some queries. Each query specifies a range [L, R], and you need to find the largest 5 distinct digital roots among all continuous sub-ranges within this range. If there are fewer than 5, fill the rest with -1.

## Input Format

The first line contains an integer N, representing the length of the sequence. The second line contains N integers Ai (0 ≤ Ai < 10^9). The third line contains an integer Q, representing the number of queries. The next Q lines each contain two positive integers l and r, representing the query range (1 ≤ l ≤ r ≤ N).

## Output Format

Output Q lines, each representing the largest 5 distinct digital roots in descending order for each query range, separated by spaces.

## Sample Input and Output

### Input Sample #1

```
5
101 240 331 4 52
3
1 3
4 5
1 5
```

### Output Sample #1

```
8 7 6 4 2
7 4 2 -1 -1
9 8 7 6 4
```

## Notes

### Sample Explanation

For the first query range [1, 3], its continuous sub-ranges are [1, 1], [2, 2], [3, 3], [1, 2], [2, 3], [1, 3]. The corresponding digital roots are 2, 6, 7, 8, 4, 6. Therefore, the largest 5 are 8, 7, 6, 4, 2.

### Data Range

30% of the data: N ≤ 1000; Q ≤ 1000

100% of the data: N ≤ 100000; Q ≤ 100000

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
