Consider an n-vertex binary search tree T containing n keys 1,2,...,n. A permutation p = \[p $ _{1} $ ,...,p $ _{n} $ \] of the integers 1,2,...,n is said to be _consistent with the tree T_ if the tree can be built from the empty one as the result of inserting integers p $ _{1} $ ,p $ _{2} $ ,...,p $ _{n} $ . Find how many permutations are consistent with the tree T.

## Input Format

The first line of the input file contains one positive integer d not larger than 10. This is the number of data sets. The data sets follow. Each set of data occupies two consecutive lines of the input file. The first line contains only one integer n, 1 <= n <= 30. This is the number of vertices of the tree. The second line contains a sequence of n integers separated by single spaces. The integers are keys in the input tree given in the prefix order. The first integer in the sequence is the key from the root of the tree. It is followed by the keys from the left subtree written in the prefix order. The sequence ends with the keys from the right subtree, also given in the prefix order.

## Output Format

For each i = 1,...,d, your program should write to the i-th line of output the number of permutations consistent with the tree described in the i-th data set.

## Sample Input and Output

### Sample Input #1

```
5 
3 
2 1 3 
3 
1 2 3 
1 
1 
4 
2 1 3 4 
4 
1 4 2 3
```

### Sample Output #1

```
2 
1 
1 
3 
1
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
