You are given two matrices, each with 6 rows and 5 columns. Your task is to determine a password based on the following rule: the i-th letter of the password from the left must appear in the i-th column from the left in both matrices.

For example:

```
Matrix 1:
A Y G S U
D O M R A
C P F A S
X B O D G
W D Y P K
P R X W O

Matrix 2:
C B O P T
D O S B G
G T R A R
A P M M S
W S X N U
E F G H I
```

In these matrices, the passwords COMPU and DPMAG satisfy the condition. For example, with COMPU: C appears in the first column of both matrices, O in the second, and so on.

Now, you are given t sets of data. Each set includes a positive integer k and two matrices. Your task is to output the k-th smallest password in lexicographical order that satisfies the condition. If no such password exists, output "NO".

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
