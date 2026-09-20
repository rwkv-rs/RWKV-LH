A set **S** of positive integers is called _strongly triple-free_ if, for any integer **x**, the sets {**x**, 2**x**} and {**x**, 3**x**} are not subsets of **S**. Let's define **F(n)** as a number of strongly triple-free subsets of {1, 2, ..., **n**}, where **n** is a natural number.

 You need to write a program which being given a number **n** calculates the number **F(n)** modulo 1 000 000 001.

## Input Format

The first line of input contains integer **T** (1 ≤ **T** ≤ 500) - the number of testcases. Then descriptions of **T** testcases follow.

 The description of the testcase consists of one line. The line contains an integer number **n** (1 ≤ **n** ≤ 100 000).

## Output Format

For each testcase in the input your program should output one line. This line should contain one integer number which is the number **F(n)** modulo 1 000 000 001.

## Sample Input and Output

### Sample Input #1

```
5
3
1
10
20
39
```

### Sample Output #1

```
5
2
198
43776
971827200
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
