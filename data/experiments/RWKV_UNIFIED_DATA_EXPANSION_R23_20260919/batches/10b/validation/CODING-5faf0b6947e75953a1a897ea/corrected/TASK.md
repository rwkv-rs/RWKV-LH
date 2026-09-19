The weather forecasting system of Company A operates as follows: It uses an integer between 0 and 4146 (inclusive) to represent the weather condition of a day. When predicting the weather for a future day, it relies on the weather conditions of the previous \( n \) days. If \( w_i \) represents the weather condition of the \( i \)-th day (\( i > n \)), then \( w_i = (a_1 \times w_{i-1} + a_2 \times w_{i-2} + \cdots + a_n \times w_{i-n}) \mod 4147 \), where \( a_1, a_2, \ldots, a_n \) are known constants. Given the weather conditions of the first \( n \) days, what is the predicted weather condition for the \( m \)-th day?

## Input Format

The first line of the input contains two positive integers \( n \) and \( m \). The second line contains \( n \) non-negative integers representing \( w_n, w_{n-1}, \ldots, w_1 \). The third line contains \( n \) non-negative integers representing \( a_1, a_2, \ldots, a_n \).

## Output Format

Output a single integer representing the predicted weather condition for the \( m \)-th day.

## Sample Input and Output

### Input Sample #1

```
2 3
4 5
6 7
```

### Output Sample #1

```
59
```

## Notes/Hints

\( 1 \le n \le 100 \), \( n < m \le 10^7 \), \( 0 \le a_i, w_i \le 4146 \).

Time limit for each test case is 1.5 seconds.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
