Given a rooted tree \( T \) with \( n \) nodes, the nodes are numbered from 1, with the root node being the 1st node, and each node has a positive integer value \( v_i \).

Let the subtree of node \( x \) (including \( x \) itself) contain nodes numbered \( c_1, c_2, \dots, c_k \). The value of node \( x \) is defined as:

\[
val(x) = (v_{c_1} + d(c_1, x)) \oplus (v_{c_2} + d(c_2, x)) \oplus \cdots \oplus (v_{c_k} + d(c_k, x))
\]

where \( d(x, y) \) represents the number of edges in the unique simple path between nodes \( x \) and \( y \) in the tree, and \( d(x, x) = 0 \). The symbol \( \oplus \) denotes the XOR operation.

You are required to compute the result of \( \sum_{i=1}^n val(i) \).

## Input Format

The first line contains a positive integer \( n \), representing the size of the tree.

The second line contains \( n \) positive integers representing \( v_i \).

The next line contains \( n-1 \) positive integers, sequentially representing the parent node numbers \( p_i \) from the 2nd node to the \( n \)-th node.

## Output Format

Output a single integer representing the answer.

## Sample Input and Output

### Input Sample #1

```
5
5 4 1 2 3
1 1 2 2
```

### Output Sample #1

```
12
```

## Notes

**Sample Explanation 1**

\( val(1) = (5+0) \oplus (4+1) \oplus (1+1) \oplus (2+2) \oplus (3+2) = 3 \).

\( val(2) = (4+0) \oplus (2+1) \oplus (3+1) = 3 \).

\( val(3) = (1+0) = 1 \).

\( val(4) = (2+0) = 2 \).

\( val(5) = (3+0) = 3 \).

The sum is \( 12 \).

**Data Range**

For 10% of the data: \( 1 \leq n \leq 2501 \);

For 40% of the data: \( 1 \leq n \leq 152501 \);

Additionally, 20% of the data: all \( p_i = i-1 \) (\( 2 \leq i \leq n \));

Additionally, 20% of the data: all \( v_i = 1 \) (\( 1 \leq i \leq n \));

For 100% of the data: \( 1 \leq n, v_i \leq 525010 \), \( 1 \leq p_i \leq n \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
