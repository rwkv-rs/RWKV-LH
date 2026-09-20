In IQ-testing games, there is always a type of elimination game. However, the Link and Erase game we are facing now is not like the one in QQ Games that tests your eyesight. Our rules are as follows: Given a closed interval \([a, b]\) of all integers, if there are two numbers \(x\) and \(y\) (\(x > y\)) such that their squared difference \(x^2 - y^2\) is a perfect square \(z^2\), and \(y\) is coprime with \(z\), then \(x\) and \(y\) can be linked and erased together, gaining \(x + y\) points. The goal is to eliminate as many pairs as possible while achieving a sufficient score. Let's calculate it manually.

## Input Format

A single line containing two integers, \(a\) and \(b\).

## Output Format

Two numbers: the number of pairs that can be erased, and the maximum score that can be obtained under this condition.

## Sample Input and Output

### Sample Input #1

```
1 15
```

### Sample Output #1

```
2 34
```

## Notes/Hints

### Data Size and Constraints

- For 30% of the data, it is guaranteed that \(1 \le a, b \le 100\).
- For 100% of the data, it is guaranteed that \(1 \le a, b \le 1000\).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
