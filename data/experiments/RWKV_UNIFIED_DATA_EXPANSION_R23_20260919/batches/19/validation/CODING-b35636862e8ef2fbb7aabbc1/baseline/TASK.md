Let us define:

- F\[1\] = 1
- F\[i\] = (a\*M\[i\] + b\*i + c)%1000000007 for i > 1

where M\[i\] is the median of the array {F\[1\], F\[2\], ..., F\[i-1\]}.

The median of an array is the middle element of that array when it is sorted. If there are an even number of elements in the array, we choose the first of the middle two elements to be the median.

Given a, b, c and n, calculate the sum F\[1\] + F\[2\] + .. + F\[n\].

## Input Format

The first line contains T the number of test cases. Each of the next T lines contain 4 integers : a, b, c and n.

## Output Format

Output T lines, one for each test case, containing the required sum.

## Sample Input and Output

### Sample Input #1

```
2
1 0 0 3
3 1 2 6
```

### Sample Output #1

```
3
103
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
