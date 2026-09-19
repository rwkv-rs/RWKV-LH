You are given n closed integer intervals \[a $ _{i} $ , b $ _{i} $ \] and n integers c $ _{1} $ , ..., c $ _{n} $ .

   
### Task

Write a program that:

- reads the number of intervals, their endpoints and integers c $ _{1} $ , ..., c $ _{n} $ from the standard input,
- computes the minimal size of a set Z of integers which has at least c $ _{i} $ common elements with interval \[a $ _{i} $ , b $ _{i} $ \], for each i = 1, 2, ..., n,
- writes the answer to the standard output.

## Input Format

The input begins with the integer t, the number of test cases. Then t test cases follow.

 For each test case the first line of the input contains an integer n (1 <= n <= 50000) - the number of intervals. The following n lines describe the intervals. Line (i+1) of the input contains three integers a $ _{i} $ , b $ _{i} $ and c $ _{i} $ separated by single spaces and such that 0 < = a $ _{i} $ < = b $ _{i} $ <= 50000 and 1 < = c $ _{i} $ < = b $ _{i} $ -a $ _{i} $ +1.

## Output Format

For each test case the output contains exactly one integer equal to the minimal size of set Z sharing at least c $ _{i} $ elements with interval \[a $ _{i} $ , b $ _{i} $ \], for each i= 1, 2, ..., n.

## Sample Input and Output

### Sample Input #1

```
1
5
3 7 3
8 10 3
6 8 1
1 3 1
10 11 1
```

### Sample Output #1

```
6
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
