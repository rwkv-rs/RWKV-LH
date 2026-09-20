Segment Tree is Little L's favorite data structure, as it can efficiently solve many practical problems.

Given a positive integer \( n \), Little L constructs a segment tree with indices in the integer interval \([1, n]\):

- Initially, the segment tree has only one node \([1, n]\).
- For a node \([L, R]\), if \( L < R \), then let \( mid = \left\lfloor \frac{L + R}{2} \right\rfloor \) (where \(\lfloor x \rfloor\) denotes the largest integer not exceeding \( x \)), Little L creates two child nodes \([L, mid]\) and \([mid + 1, R]\).

Little L defines a function \( cover(a, b) \) (\( 1 \le a \le b \le n \)) which represents the minimum number of segment tree nodes needed to completely cover the interval \([a, b]\) without overlap.

Little L attempts to use this segment tree to solve a complex problem and wants to roughly evaluate its performance.

Specifically, the interval \([1, n]\) has \(\frac{n (n + 1)}{2}\) different subintervals. If Little L randomly selects one of these \(\frac{n (n + 1)}{2}\) subintervals with equal probability and denotes it as \([A, B]\), then Little L believes the expected value of \( cover(A, B) \) can be used to evaluate the performance of this segment tree.

Little L asks you to calculate the product of the expected value of \( cover(A, B) \) and \(\frac{n (n + 1)}{2}\), modulo \( 1,000,000,007 \). It can be observed that this result is always an integer.

## Input Format

The first line contains a positive integer \( T \) (\( 1 \le T \le 1000 \)), indicating the number of test cases.  
The next \( T \) lines, each containing a positive integer \( n \) (\( 1 \le n \le 10^{18} \)), represent the \( n \) for each test case.

## Output Format

Output \( T \) lines, each containing an integer representing the answer for the corresponding test case.

## Sample Input and Output

### Sample Input #1

```
1
3
```

### Sample Output #1

```
7
```

## Notes

**[Sample Explanation #1]**

\( cover(1, 1) = 1 \), \( cover(2, 2) = 1 \), \( cover(3, 3) = 1 \), \( cover(1, 2) = 1 \), \( cover(2, 3) = 2 \), \( cover(1, 3) = 1 \). Therefore, the expected value of \( cover(A, B) = \frac{1 + 1 + 1 + 1 + 2 + 1}{6} = \frac{7}{6} \).

**[Problem Source]**

This problem is from the 2021 Tsinghua University Student Programming Contest and University Invitational Competition (THUPC2021) Preliminary Round.

Solutions and other resources can be found at <https://github.com/THUSAAC/THUPC2021-pre>.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
