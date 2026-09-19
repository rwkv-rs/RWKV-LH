Consider the following exercise, found in a generic linear algebra textbook.Let A be an n × n matrix. Prove that the following statements are equivalent:

- (a) A is invertible.
- (b) Ax = b has exactly one solution for every n × 1 matrix b.
- (c) Ax = b is consistent for every n × 1 matrix b.
- (d) Ax = 0 has only the trivial solution x = 0.

The typical way to solve such an exercise is to show a series of implications. For instance,one can proceed by showing that (a) implies (b), that (b) implies (c), that (c) implies (d),and ﬁnally that (d) implies (a). These four implications show that the four statements are equivalent. Another way would be to show that (a) is equivalent to (b) (by proving that (a) implies (b) and that (b) implies (a)), that (b) is equivalent to (c), and that (c) is equivalent to (d).

  
However, this way requires proving six implications, which is clearly a lot more work than just proving four implications! I have been given some similar tasks, and have already started proving some implications. Now I wonder, how many more implications do I have to prove? Can you help me determine this ?

## Input Format

On the ﬁrst line one positive number: the number of testcases, at most 100. After that per testcase:

- One line containing two integers n (1
- m lines with two integers s1 and s2 (1

## Output Format

Per testcase:  
One line with the minimum number of additional implications that need to be proved in order to prove that all statements are equivalent.

## Sample Input and Output

### Sample Input #1

```
\n2\n4 0\n3 2\n1 2\n1 3\n\n
```

### Sample Output #1

```
\n4\n2\n
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
