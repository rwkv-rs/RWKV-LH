## Problem Description

qwqwq.

How much damage does the Blue Dragon's Desecration deal?

-------

qwq always fails to cast Textbook Desecration in Hearthstone, so he rewrote a version of 'Hearthstone' and changed the description of Desecration to: "Randomly select an integer as the damage value \( d \) from the interval \([L, R]\), and deal \( d \) points of damage to all minions. If any minion dies, cast the spell again with the same damage value; if no minion dies, stop casting." He also removed the limit on the number of minions on the field and the restriction that Desecration can trigger up to 14 times. qwq is unsure how this modified Desecration works, so he plans to conduct some tests, involving a total of \( m \) operations of the following types:

1. Add a minion with health \( h \) to the field, where the health of minions cannot exceed \( n \);

2. Given \([L, R]\), query the expected number of times Desecration is triggered; qwq can only perform operation 1, so he handed operation 2 over to you.

## Input Format

The first line contains two integers \( n \) and \( m \) separated by a space. The next \( m \) lines each represent an operation, where operation 1 is denoted as \( 1 \ h \) and operation 2 is denoted as \( 2 \ L \ R \).

## Output Format

To avoid outputting decimals, for each operation 2, output an integer representing the product of the expected value and \((R-L+1)\).

## Sample Input and Output

### Input Sample #1

```
10 10
2 7 9
1 6
2 7 10
1 10
1 7
2 7 10
1 7
1 1
2 6 7
1 4
```

### Output Sample #1

```
3
8
11
6
```

## Notes

For 19% of the data, \( n, m \leq 10^3 \).

For another 19% of the data, each operation 2 satisfies \( L = R \).

For another 19% of the data, all operation 2s occur after all operation 1s.

For another 19% of the data, \( m \leq 10^5 \).

For 100% of the data, it is guaranteed that: \( 1 \leq n \leq 10^5 \), each operation 1 has \( 1 \leq h \leq n \), each operation 2 has \( 1 \leq L \leq R \leq n, 1 \leq m \leq 10^6 \); all the above values are integers.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
