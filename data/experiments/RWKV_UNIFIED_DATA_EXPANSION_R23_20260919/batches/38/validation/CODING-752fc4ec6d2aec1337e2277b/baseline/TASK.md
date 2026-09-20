According to some books, God's failed attempt at creation went like this:

On the first day, God created the basic elements of the world, called "meta."

On the second day, God created a new element called $\alpha$. $\alpha$ is defined as the set of meta. It's easy to see that there are exactly two different $\alpha$s.

On the third day, God created another new element called $\beta$. $\beta$ is defined as the set of $\alpha$. It's easy to see that there are exactly four different $\beta$s.

On the fourth day, God created a new element $\gamma$, which is defined as the set of $\beta$. Obviously, there will be 16 different $\gamma$s.

If this continues, the fourth element God creates will have 65536 types, and the fifth element will have $2^{65536}$ types. This will be an astronomical number.

However, God did not anticipate that the growth of the number of element types would be so rapid. He wanted the world to be rich in elements, so day after day, year after year, he kept creating new elements...

But soon, when God created the last element $\theta$, he found that there were too many elements in the world, so many that the world could not bear it. So on that day, God destroyed the world.

To this day, God still remembers that failed attempt at creation. Now he wants to ask you, how many types of the last element $\theta$ were there?

God thinks this number might be too large to express, so you only need to answer the value of this number modulo $p$.

You can assume that God created elements from $\alpha$ to $\theta$ a total of $10^9$ times, or $10^{18}$ times, or even infinitely many times.

In short, define $a_0=1, a_n=2^{a_{n-1}}$. It can be proven that $b_n=a_n \bmod p$ will be the same value after a certain point. Find this value.

## Input Format

The first line contains an integer $T$, indicating the number of test cases.

Next, $T$ lines each contain a positive integer $p$, which is the modulus you need to use.

## Output Format

Output $T$ lines, each containing a positive integer, which is the answer modulo $p$.

## Sample Input and Output

### Sample Input #1

```
3
2
3
6
```

### Sample Output #1

```
0
1
4
```

## Notes/Hints

For $100\%$ of the data, $T \le 10^3$, $p \le 10^7$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
