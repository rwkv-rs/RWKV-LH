There are two sets of numbers, each containing \( k \) numbers.

The numbers in the first set are denoted as \( a_1, a_2, \cdots, a_k \), and the numbers in the second set are denoted as \( b_1, b_2, \cdots, b_k \).

The numbers in the second set are pairwise coprime. Find the smallest \( n \in \mathbb{N} \) such that for all \( i \in [1, k] \), \( b_i \) divides \( n - a_i \).

## Input Format

The first line contains an integer \( k \).

The second line contains \( k \) integers: \( a_1, a_2, \cdots, a_k \).

The third line contains \( k \) integers: \( b_1, b_2, \cdots, b_k \).

## Output Format

Output a single integer, which is the required answer \( n \).

## Sample Input and Output

### Sample Input #1

```
3
1 2 3
2 3 5
```

### Sample Output #1

```
23
```

## Notes/Hints

For \( 100\% \) of the data:

\( 1 \le k \le 10 \), \( |a_i| \le 10^9 \), \( 1 \le b_i \le 6 \times 10^3 \), \( \prod_{i=1}^k b_i \le 10^{18} \).

Each test case has a time limit of 1 second.

Note: For ```C/C++``` language, 64-bit integers should be declared as ```long long```.

When using ```scanf```, ```printf``` functions (and similar ones like ```fscanf```, ```fprintf```), use the ```%lld``` specifier.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
