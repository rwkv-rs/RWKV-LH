Legend has it that in the ancient era when the world was just formed, there was only one type of flower called "Yuan." Then, a magical fairy appeared who could imbue flowers with attributes. From then on, "Yuan" began to mutate, giving rise to the myriad of diverse flowers in the vast world. It is said that the fairy can exist in a two-dimensional space (plane), a three-dimensional space (solid), and even an $n$-dimensional space (imagination). A point in a two-dimensional space can be represented by a vector $\left(x_1, x_2\right)$, a point in a three-dimensional space by a vector $\left(x_1, x_2, x_3\right)$, and generally, a point in an $n$-dimensional space by a vector $\left(x_1, x_2, \cdots, x_n\right)$. The distance between two points $\left(x_1, x_2, \cdots, x_n\right)$ and $\left(w_1, w_2, \cdots, w_n\right)$ in an $n$-dimensional space is defined as $\sqrt{\sum_{i=1}^{n}(X_i-W_i)^2}$. In an $n$-dimensional space, every time the fairy casts a spell, she chooses a reference point $\left(w_1, w_2, \cdots, w_n\right)$ and an action radius $r$, with the position of the reference point and the size of the action radius being arbitrarily selectable. At this time, all flowers in the $n$-dimensional space whose distance from the reference point $\left(w_1, w_2, \cdots, w_n\right)$ is less than the action radius $r$ will be affected by this spell. Each spell imparts different attributes to the affected flowers, and the effects can be cumulative. Generally, if the fairy casts a total of $m$ spells, the attributes of a flower at a certain point in the $n$-dimensional space can be described by a binary string of length $m$, $\left(a_1, a_2, \cdots, a_n\right)$, where for $1 \le i \le m$, if the flower is affected by the $i$-th spell, then $a_i$ is $1$, otherwise it is $0$. Obviously, different attributes correspond to different flowers. The question now is: After the fairy casts $m$ spells in an $n$-dimensional space, how many different types of flowers can she obtain at most?

## Input Format

The input contains two integers separated by a space. The first integer represents the number of spells cast, $m$, and the second integer represents the dimension of the space, $n$. Here, $1 \le m \le 100$ and $1 \le n \le 15$.

## Output Format

Output a single integer on one line, which is the answer.

## Sample Input and Output

### Sample Input #1

```
3 1
```

### Sample Output #1

```
6
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
