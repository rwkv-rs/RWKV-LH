Not long after the start of the first semester, the students of Class E are going on a school trip!

## Problem Description

Now, six individuals - Akabane Karma, Sugano Tomo, Okuda Aimi, Kayano Akane, Kanzaki Yukiko, and Shiota Nagisa - are grouped together. They will be conducting an assassination trip in Kyoto. Their target remains the same: to assassinate the teacher. The government has also sent professional snipers, the Crimson Eyes. However, while completing their mission, they want to maximize their happiness.

The clever Kanzaki Yukiko has finally derived the expression for happiness, which is shocking because it turns out that happiness is related to the number of tourist spots and the number of times they assassinate the teacher!

Suppose they visit \( n \) tourist spots and assassinate the teacher \( m \) times. Define:

$$
\Gamma(a,b)=\left\{
    \begin{aligned}
    & 1, & a > b \\
    & \prod_{i=a}^b i, & a \le b \\
    \end{aligned}
    \right.
$$

Then the happiness is:

$$
\sum_{i=0}^m \left( \frac{\sqrt{\sum_{j=0}^i (C_i^j)^2C_{n+2i-j}^{2i}}}{\Gamma(n+1,n+i)} \times \Gamma(n-i+1,n) \right)
$$

**We guarantee** that \(\frac{\sqrt{\sum_{j=0}^i (C_i^j)^2C_{n+2i-j}^{2i}}}{\Gamma(n+1,n+i)} \times \Gamma(n-i+1,n)\) **is an integer.**

Now they have \( T \) questions for you. If they visit \( n \) tourist spots and assassinate the teacher \( m \) times, can you tell them the happiness value?

**Since the answer may be very large, please output the answer modulo \( 998244353 \).**

## Input and Output Format

### Input Format

**This problem contains multiple test cases.**

The first line contains an integer \( T \), representing the number of test cases.

For each test case:

There is one line with two integers \( n \) and \( m \).

### Output Format

For each test case, output one line with an integer representing the happiness value after visiting \( n \) tourist spots and assassinating the teacher \( m \) times, modulo \( 998244353 \).

### Sample Input and Output

#### Input Sample #1

```
5
5 3
7 3
9 6
100 50
44 22
```

#### Output Sample #1

```
26
64
466
41441083
461961723
```

## Notes

### Data Range

**This problem uses bundled testing.**

- Subtask 1 (10 points): \( T \leq 10 \), \( n, m \leq 10 \).
- Subtask 2 (20 points): \( T \leq 100 \), \( n, m \leq 5 \times 10^4 \).
- Subtask 3 (30 points): \( T \leq 50 \), \( n, m \leq 9 \times 10^8 \).
- Subtask 4 (40 points): No special limitations on the data.

For \( 100\% \) of the data, \( m \leq n \), \( 1 \leq T \leq 10^2 \), \( 1 \leq n, m \leq 9 \times 10^8 \).

---
### Hints

**The time limit for the third subtask is 2 seconds, and for the fourth subtask is 5 seconds.**

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
