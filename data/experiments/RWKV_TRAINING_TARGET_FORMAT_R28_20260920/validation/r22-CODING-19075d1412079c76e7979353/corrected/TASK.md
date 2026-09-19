Little Willy just took a compilers course and is trying to implement his own compiler. First he wants to build a table with all the possible ids that a program could have. He knows that his language supports up to N different characters and any id can be up to L characters long. For example, when N = 2 (lets say characters can be 0 or 1), and L = 3, he could have the following ids: {0, 1, 00, 01, 10, 11, 000, 001, 010, 011, 100, 101, 110, 111}.

You have to write a program that can help Willy find out the size of the table. Since the answer can be really big, you must print it modulo 1000000007 (10^9+7).

## Input Format

The input contains several test cases. Each test case will consist of a single line containing two integers N and L. N is the number of characters that can be part of an id and L is maximum lenght supported by the language (1 <= N <= 65535, 1 <= L <= 10^5).

End of the input is indicated by a test case with N = 0, L = 0 that should not be processed.

## Output Format

For each test case output a single line containing the number of possible ids modulo 10^9+7.

## Sample Input and Output

### Sample Input #1

```
2 3\n128 32\n0 0
```

### Sample Output #1

```
14\n792805767
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
