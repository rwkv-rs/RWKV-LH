Captain Obvious has foiled the evil plans of Rabbit-Man, who has now learned some advanced arithmetic. To understand Rabbit-Man's new strategy, let's define the sequence \( F_n \) (similar to the Fibonacci sequence):

\[ F_1 = 1, \]
\[ F_2 = 2, \]
\[ F_n = F_{n-1} + F_{n-2} \text{ for } n \ge 3. \]

Rabbit-Man has integrated all his previous evil ideas into one master plan. On the \( i \)-th day, he performs a malicious act at location number \( p(i) \), defined as:

\[ p(i) = a_1 \cdot F_1^i + a_2 \cdot F_2^i + \cdots + a_k \cdot F_k^i. \]

The number \( k \) and the integer coefficients \( a_1, \cdots, a_k \) are fixed. Captain Obvious knows \( k \) but not the coefficients. Given \( p(1), p(2), \cdots, p(k) \), help Captain Obvious determine \( p(k+1) \). To avoid overwhelmingly large numbers, all calculations should be done modulo a fixed prime number \( M \). You may assume that \( F_1, F_2, \cdots, F_n \) are pairwise distinct modulo \( M \). There always exists a unique solution for the given input.

## Input Format

The first line of input contains the number of test cases \( T \). Each test case is described as follows:

- The first line contains two integers \( k \) and \( M \) where \( 1 \le k \le 4000 \) and \( 3 \le M \le 10^9 \).
- The second line contains \( k \) space-separated integers representing the values of \( p(1), p(2), \cdots, p(k) \) modulo \( M \).

## Output Format

For each test case, print a single line containing one integer: the value of \( p(k+1) \) modulo \( M \).

## Sample Input and Output

### Input Sample #1

```
2
4 619
5 25 125 6
3 101
5 11 29
```

### Output Sample #1

```
30
83
```

## Notes/Hints

Time limit: 6 seconds, Memory limit: 128 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
