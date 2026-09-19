Given a numeric string \( s \) and a positive integer \( d \), count how many different permutations of \( s \) are divisible by \( d \) (leading zeros are allowed). For example, "123434" has 90 permutations that are divisible by 2, with 30 ending in 2 and 60 ending in 4.

## Input Format

The first line of input is an integer \( T \), representing the number of test cases. Each subsequent line contains a pair \( s \) and \( d \), separated by a space. \( s \) is guaranteed to consist only of digits 0 through 9.

## Output Format

For each test case, output a single line representing the number of permutations of \( s \) that are divisible by \( d \).

## Sample Input and Output

### Input Sample #1

```
7
000 1
001 1
1234567890 1
123434 2
1234 7
12345 17
12345678 29
```

### Output Sample #1

```
1
3
3628800
90
3
6
1398
```

## Notes

100% of the data satisfies: The length of \( s \) does not exceed 10, \( 1 \le d \le 1000 \), and \( 1 \le T \le 15 \).

In the first three examples, the permutations are 1, 3, and 3628800, all of which are multiples of 1.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
