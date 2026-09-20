Alice and Bob have invented a new game. Given a sequence \(\{x_0, x_1, \cdots, x_{n-1}\}\), Alice receives a sequence \(\{a_0, a_1, \cdots, a_{n-1}\}\), where \(a_i\) represents the length of the longest increasing subsequence ending at \(x_i\); Bob receives a sequence \(\{b_0, b_1, \cdots, b_{n-1}\}\), where \(b_i\) represents the length of the longest decreasing subsequence starting at \(x_i\). Alice's score is the sum of the sequence \(\{a_i\}\), and Bob's score is the sum of the sequence \(\{b_i\}\).

## Input Format

The first line of input is \(n\), and the second line is the sequence \(\{a_0, a_1, \cdots, a_{n-1}\}\). The data guarantees that the sequence \(\{a_i\}\) can be derived from at least one permutation of numbers from 1 to \(n\).

## Output Format

The output consists of one line, indicating the highest score Bob can achieve given the sequence \(\{a_i\}\).

## Sample Input and Output

### Sample Input #1

```
4
1 2 2 3
```

### Sample Output #1

```
5
```

### Sample Input #2

```
4
1 1 2 3
```

### Sample Output #2

```
5
```

## Notes

### Data Range

For 30% of the data, \(N \le 1000\).

For 100% of the data, \(N \le 10^5\).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
