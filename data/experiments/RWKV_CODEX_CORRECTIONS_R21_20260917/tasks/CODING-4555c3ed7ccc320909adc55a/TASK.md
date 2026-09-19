## Problem Description

Lili and Lunlun have arrived at a magic shop, which contains $n$ gifts. The gifts are numbered from $1$ to $n$, where the charm value of the $i$-th gift is $c_i$ and its price is $v_i$.

The two wish to purchase some gifts, but their requirements are peculiar: Suppose the set of purchased gifts is $S = \{s_1, s_2, \dots, s_p\} (1 \leq s_i \leq n)$. They require that for any non-empty subset $T = \{t_1, t_2, \dots, t_q\}$ of $S$, the XOR sum of the charm values of all gifts in $T$ is not zero, i.e., $c_{t_1} \oplus c_{t_2} \oplus \cdots \oplus c_{t_q} \neq 0$. Here, $\oplus$ denotes the XOR operation. On top of this, they also want the number of purchased gifts to be as large as possible.

For example: $c_1 = 1, c_2 = 2, c_3 = 5, c_4 = 6, c_5 = 7$. Then $S_1 = \{2, 3, 5\}$ does not meet the requirement because $c_2 \oplus c_3 \oplus c_5 = 0$. $S_2 = \{1, 2, 3\}$ and $S_3 = \{2, 4, 5\}$ meet the requirement as any non-empty subset's XOR sum is not zero. $S_4 = \{1, 2\}$ does not meet the requirement because it does not contain the maximum number of gifts.

There may be many gift sets that meet their requirements. Therefore, the shop owner has selected two such sets $A$ and $B$ (clearly, they contain the same number of gifts). Lunlun likes set $A$, but Lili prefers set $B$. To persuade Lili to buy set $A$, Lunlun decides to use magic to alter the prices. More specifically, Lunlun can spend $(x - v_i)^2$ magic points to change the price of the $i$-th gift to any integer $x$, and each gift can only be repriced once.

Lunlun wants the repriced set $A$ to be the one with the smallest total price among all valid gift sets, and set $B$ to be the one with the largest total price (the total price of a gift set is the sum of the prices of all gifts it contains). Now, please help Lunlun calculate the minimum amount of magic points he needs to achieve his goal.

## Input Format

The first line contains two integers $n$ and $m$, representing the total number of gifts and the number of gifts in sets $A$ and $B$, respectively.

The second line contains $n$ integers $c_i$, where the $i$-th integer represents the charm value of the $i$-th gift.

The third line contains $n$ integers $v_i$, where the $i$-th integer represents the price of the $i$-th gift.

The fourth line contains $m$ integers $a_i$, representing the indices of the gifts in set $A$. It is guaranteed that the $a_i$ are distinct.

The fifth line contains $m$ integers $b_i$, representing the indices of the gifts in set $B$. It is guaranteed that the $b_i$ are distinct.

It is guaranteed that $1 \leq a_i, b_i \leq n$, and both sets $A$ and $B$ meet the requirements of the two.

## Output Format

A single integer representing the minimum magic points Lunlun needs to spend.

## Sample Input and Output

### Input Sample #1

```
5 3
1 2 5 6 7
4 4 2 1 3
1 2 3
2 4 5
```

### Output Sample #1

```
6
```

## Notes

### Sample 1 Explanation

The valid gift sets are: $\{1, 2, 3\}$, $\{1, 2, 4\}$, $\{1, 2, 5\}$, $\{1, 3, 4\}$, $\{1, 3, 5\}$, $\{2, 3, 4\}$, $\{2, 4, 5\}$, $\{3, 4, 5\}$.

An optimal reprice scheme is: $c_1 = c_2 = c_4 = c_5 = 3$, $c_3 = 2$.

### Sample 2

See the attached file `shop2.in` and `shop2.ans`.

### Sample 3

See the attached file `shop3.in` and `shop3.ans`.

### Data Range

For all test cases: $1 \leq n \leq 1000$, $1 \leq m \leq 64$, $1 \leq c_i < 2^{64}$, $0 \leq v_i \leq 10^6$.

Specific limits for each test point are as follows:

| Test Point | $n \leq$ | $m \leq$ | Special Constraints |
| :--------: | :------: | :------: | :----------------: |
| 1 - 3      | 10       | 4        | $1 \leq v_i \leq 5$ |
| 4 - 6      | 50       | 2        | $1 \leq v_i \leq 10$ |
| 7 - 10     | 500      | 30       | $0 \leq v_i \leq 1$ |
| 11 - 12    | 1000     | 64       | $A$ and $B$ are the same |
| 13 - 20    | 1000     | 64       | None |

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
