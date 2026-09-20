Rumia: Let me start by testing you with an elementary math problem!

Cirno: Sure! I'm definitely good with elementary problems!

## Problem Description

Rumia: There are \( n \) fairies who need to cross the Misty Lake. Due to the heavy fog around the lake, the fairies cannot see how large the lake is and do not want to go around its edges.

There is a ~~boat~~ teleporter on the lake, and this teleporter can only carry \( r \) fairies across the lake at a time (note that the teleporter can simultaneously transport fairies from both sides to the opposite side, but the total number of fairies transported each time cannot exceed \( r \)).

These fairies also love to cause trouble, so at any moment, certain conditions must be met. There are \( m_1 \) conditions of the first type and \( m_2 \) conditions of the second type.

The first type of condition is that fairy \( a \) and fairy \( b \) must be on the same side of the lake;

The second type of condition is that when fairy \( a \) is on one side of the lake, fairy \( b \) and fairy \( c \) cannot be on the opposite side of the lake.

Given these conditions, find:

1. The minimum number of times the teleporter needs to be used to get all the fairies to the other side of the lake.
2. Under the premise of ensuring the minimum number of times, find the number of crossing schemes.

## Input Format

The first line contains four integers \( n \), \( m_1 \), \( m_2 \), and \( r \).

The next \( m_1 \) lines each contain two integers \( a \) and \( b \), representing the first type of condition.

The next \( m_2 \) lines each contain three integers \( a \), \( b \), and \( c \), representing the second type of condition.

## Output Format

Two integers, the minimum number of teleporter uses and the number of schemes, separated by a space.

If it is impossible to get all the fairies across the lake, output "-1 0" (without quotes).

## Sample Input and Output

### Sample Input #1

```
1 0 0 1
```

### Sample Output #1

```
1 1
```

### Sample Input #2

```
5 0 0 2
```

### Sample Output #2

```
3 90
```

### Sample Input #3

```
3 1 0 1
1 2
```

### Sample Output #3

```
-1 0
```

## Notes

For \( 30\% \) of the data, \( n \leq 10 \).

For another \( 10\% \) of the data, \( m_1 = m_2 = 0 \).

For \( 100\% \) of the data, \( a, b, c \leq n \leq 15 \), \( m_1, m_2 \leq 50 \), \( r \leq 10^9 \).

Do not trust the speed of the Luogu judge machine. If you score above 80 points, try submitting again during off-peak hours. But if you score below 60 points, it might mean your solution is not correct, so don't stress the cute judge machine too much.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
