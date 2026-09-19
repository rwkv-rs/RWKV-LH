Little A has been searching for his dad recently, using a method called DNA comparison.

Little A has his own method for comparing DNA sequences, with the ultimate goal of maximizing the similarity between two DNA sequences. The steps are as follows:

1. Two DNA sequences are given, the first of length $n$ and the second of length $m$.

2. Insert any number of spaces at any position in both sequences to make the strings of equal length.

3. Match each position sequentially. **If the characters at the same position in both sequences are not spaces**, let's assume the first is $x$ and the second is $y$, then their similarity is defined by $d(x,y)$. For any extremely long segment of length $k$ of consecutive spaces in both sequences, we define the similarity of this space segment as $g(k) = -A - B(k-1)$.

The final similarity of the two sequences is the sum of all $d(x,y)$ plus the sum of the similarities of all extremely long space segments.

Now, Little A has obtained a segment of Little B's DNA sequence through some mysterious means, and he wants you to help him calculate the maximum similarity between Little A's and Little B's DNA sequences.

## Input Format

The first line of input is a string representing Little A's DNA sequence.

The second line of input is a string representing Little B's DNA sequence.

The next four lines, each containing four integers separated by spaces, represent the $d$ array in the following order:

```plain
d(A,A) d(A,T) d(A,G) d(A,C)
d(T,A) d(T,T) d(T,G) d(T,C)
d(G,A) d(G,T) d(G,G) d(G,C)
d(C,A) d(C,T) d(C,G) d(C,C)
```
The last line contains two positive integers $A$ and $B$, as described in the problem.

## Output Format

Output a single line representing the maximum similarity between the two sequences.

## Sample Input and Output

### Sample Input #1

```
ATGG
ATCC
5 -4 -4 -4 
-4 5 -4 -4 
-4 -4 5 -4 
-4 -4 -4 5 
2 1
```

### Sample Output #1

```
4
```

## Notes

### Sample Explanation

First, extend the sequences to the following form (where "-" represents a space):

```cpp
ATGG--
AT--CC
```
Then, the sum of all $d(x,y)$ is $d(A,A) + d(T,T) = 10$.

The sum of the similarities of all extremely long space segments is $g(2) + g(2) = -6$.

The total sum is $4$, which can be verified as the maximum similarity.

For all test cases, the conditions are $0 < B < A \le 1000, -1000 \le d(x,y) \le 1000, d(x,y) = d(y,x)$, and the sequences only contain the characters ${A, T, G, C}$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
