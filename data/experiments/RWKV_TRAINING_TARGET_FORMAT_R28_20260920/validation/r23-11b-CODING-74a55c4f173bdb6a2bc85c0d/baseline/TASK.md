**Problem Description**

LISP is one of the earliest high-level programming languages, similar to FORTRAN, and is also one of the oldest languages still in use today. The fundamental data structure used in LISP is the list, which can be used to represent other important data structures, such as trees.

This problem determines whether a binary tree, represented by a LISP S-expression, possesses a specific property.

Given a binary tree of integers, write a program to determine if there exists a path from the tree root to a leaf such that the sum of the nodes along the path equals a specific integer. For example, the tree illustrated below has four such paths from the root to the leaves, with sums of 27, 22, 26, and 18.

The input binary tree is represented using LISP S-expressions, as shown below:
- empty tree ::= ()
- tree ::= empty tree (integer tree tree)

The tree given in the above diagram is represented as the expression: `(5 (4 (11 (7 () ()) (2 () ()) ) ()) (8 (13 () ()) (4 () (1 () ()) ) ) )`.

In this expression, all leaves of the tree are represented as `(integer () () )`.

Since an empty tree has no path from the root to the leaf, the answer to whether there exists a path with a sum equal to a specific number in an empty tree is negative.

**Input**

The input contains a series of test cases. Each test case consists of an integer followed by one or more spaces, followed by a binary tree represented in the above-defined S-expression format. All S-expressions are valid binary tree representations, although the expression may span several lines and can contain various spaces. The input consists of one or more test cases, ending with the end of the file.

**Output**

For each test case (integer/tree) in the input, output one line. For each `I, T` (where `I` is an integer, and `T` is a tree), output "yes" if there exists a path from the root to a leaf in `T` such that the sum is `I`. Otherwise, output "no".

**Sample Input**

```
22 (5(4(11(7()())(2()()))()) (8(13()())(4()(1()()))))
20 (5(4(11(7()())(2()()))()) (8(13()())(4()(1()()))))
10 (3 
(2 (4 () () )
(8 () () ) )
(1 (6 () () )
(4 () () ) ) )
5 ()
```

**Sample Output**

```
yes
no
yes
no
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
