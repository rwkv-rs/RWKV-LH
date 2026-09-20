Pòlya has acquired a magical pocket adorned with symbols incomprehensible to humans. Fascinated, Pòlya pondered deeply and discovered a magical model (later known as the Pòlya model). To vividly teach this model, he conducted a virtual game with his students: At the start of the game, the pocket contains $a_1$ balls of color 1, $a_2$ balls of color 2, ..., $a_t$ balls of color $t$, where $a_i \in \mathbb Z^+$ ($1 \le i \le t$).

The game strictly follows these operations:

Randomly draw a ball from the pocket (all balls have an equal chance of being drawn), Pòlya observes its color and then places it back, adding $d$ more balls of the same color to the pocket.

Let $c_i$ denote the color of the ball drawn in the $i$-th draw ($1 \le c_i \le t$). A game session will generate a sequence of colors ($c_1, c_2, \ldots, c_n, \ldots$). Pòlya informs all students of the initial number of balls of each color $a_1, a_2, \ldots, a_t$. He then asks the students: What is the probability that a game session's color sequence satisfies the following conditions?

$$c_{x_1}=y_1, c_{x_2}=y_2, \ldots, c_{x_n}=y_n$$

where $0 < x_1 < x_2 < \cdots < x_n$ and $1 \le y_i \le t$. In other words, given $(t, n, d, a_1, a_2, \ldots, a_t, x_1, y_1, x_2, y_2, \ldots, x_n, y_n)$, you need to determine the likelihood of the event: "For all $k$ ($1 \le k \le n$), the color of the ball drawn in the $x_k$-th draw is $y_k$."

## Input Format

The first line contains three positive integers $t, n, d$.

The second line contains $t$ positive integers $a_1, a_2, \ldots, a_t$, representing the initial number of balls of each color in the pocket.

The following $n$ lines each contain two positive integers $x_i, y_i$, indicating that the $x_i$-th draw results in a ball of color $y_i$.

## Output Format

Output the probability in fractional form (clearly, this probability is a rational number). The output file should contain one line in the format: `numerator/denominator`. Ensure the fraction is in its simplest form (numerator and denominator are coprime). Specifically, if the probability is $0$, output `0/1`, and if it is $1$, output `1/1`.

## Sample Input and Output

### Sample Input #1

```
2 3 1
1 1
1 1
2 2
3 1
```

### Sample Output #1

```
1/12
```

### Sample Input #2

```
3 1 2
1 1 1
5 1
```

### Sample Output #2

```
1/3
```

## Notes

**[Sample Explanation #1]**

Initially, the counts of the two colors are $(1, 1)$. The probability of drawing a ball of color 1 is $1/2$; before the second draw, the counts are $(2, 1)$, and the probability of drawing a ball of color 2 is $1/3$; before the third draw, the counts are $(2, 2)$, and the probability of drawing a ball of color 1 is $1/2$. Therefore, the total probability of the three draws is $1/12$.

**[Data Range and Constraints]**

For $100\%$ of the data, $1 \le t, n \le 1000$, $1 \le a_k, d \le 10$, $1 \le x_1 < x_2 < \cdots < x_n \le 10000$, $1 \le y_k \le t$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
