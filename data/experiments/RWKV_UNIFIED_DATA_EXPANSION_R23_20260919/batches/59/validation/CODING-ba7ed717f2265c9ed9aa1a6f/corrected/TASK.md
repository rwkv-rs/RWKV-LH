Every day, Danny buys one sweet from the candy store and eats it. The store has $m$ types of sweets, numbered from $1$ to $m$. Danny knows that a balanced diet is important and is applying this concept to his sweet purchasing. To each sweet type $i$, he has assigned a target fraction, which is a real number $f_i$ ($0 \le f_i \le 1$). He wants the fraction of sweets of type $i$ among all sweets he has eaten to be roughly equal to $f_i$.

To be precise, let $s_i$ denote the number of sweets of type $i$ that Danny has eaten, and let $n = \sum_{i=1}^m s_i$. We say the set of sweets is balanced if for every $i$ we have:

\[ n f_i - 1 < s_i < n f_i + 1. \]

Danny has been buying and eating sweets for a while and during this entire time the set of sweets has been balanced. He is now wondering how many more sweets he can buy while still fulfilling this condition. Given the target fractions $f_i$ and the sequence of sweets he has eaten so far, determine how many more sweets he can buy and eat so that at any time the set of sweets is balanced.

## Input Format

The input consists of three lines. The first line contains two integers $m$ ($1 \le m \le 10^5$), which is the number of types of sweets, and $k$ ($0 \le k \le 10^5$), which is the number of sweets Danny has already eaten.

The second line contains $m$ positive integers $a_1, \ldots, a_m$. These numbers are proportional to $f_1, \ldots, f_m$, that is, $\displaystyle f_i = \frac{a_i}{\sum_{j=1}^m a_j}$. It is guaranteed that the sum of all $a_j$ is no larger than $10^5$.

The third line contains $k$ integers $b_1, \ldots, b_k$ ($1 \le b_i \le m$), where each $b_i$ denotes the type of sweet Danny bought and ate on the $i^{\text{th}}$ day. It is guaranteed that every prefix of this sequence (including the whole sequence) is balanced.

## Output Format

Display the maximum number of additional sweets that Danny can buy and eat while keeping his diet continuously balanced. If there is no upper limit on the number of sweets, display the word `forever`.

## Sample Input and Output

### Sample Input #1

```
6 5
2 1 6 3 5 3
1 2 5 3 5
```

### Sample Output #1

```
1
```

### Sample Input #2

```
6 4
2 1 6 3 5 3
1 2 5 3
```

### Sample Output #2

```
forever
```

## Notes/Hints

Time limit: 2000 ms, Memory limit: 1048576 kB.

International Collegiate Programming Contest (ACM-ICPC) World Finals 2016

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
