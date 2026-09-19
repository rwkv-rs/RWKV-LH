Zhencheng Ocean recently needs to purchase a large quantity of Seth Stones. You might ask, what is a Seth Stone?

First, let's understand the unit of weight called Seth, denoted as $si$. For example, $1$ Seth is $1si$.

Seth Stones have a unique property: they initially exist as individual units of $1si$ each. However, after being refined with a natural gun, they can merge with other refined Seth Stones. Once they reach an appropriate weight, they are dulled to prevent further merging. If the merging is incorrect, they can be cut with a diamond knife into integer Seth weights. The weight of Seth Stones can only be an **integer** Seth weight, and the price of Seth Stones varies with different weights.

## Problem Description

A seller needs to market a Seth Stone weighing $Need$ Seths. The seller wants to calculate the maximum profit that can be achieved through a certain merging method. However, there is a problem: the market is near the Zhencheng Hall (the central location of Zhencheng Ocean), and the seller needs to rent boats to transport the Seth Stones (i.e., the cost of the seller renting a boat is not considered). Currently, there are ten types of boats available for rent, with carrying capacities from $1si$ to $10si$, and each boat has a different rental price, as shown in the table below:

![](https://cdn.luogu.com.cn/upload/pic/10663.png)

Due to the strong Seth force near the Zhencheng Hall, **no operations can be performed on the Seth Stones**, and they can only be sold as merged. Assuming the seller does not return, and all the Seth Stones can be sold. The seller needs to calculate the total profit (total profit = total revenue from Seth Stones - total boat rental cost). Please design a program to calculate the best scheme to achieve the **maximum total profit**.

## Input Format

The input consists of two lines:

- The first line contains one data $Need$ (the total weight of the Seth Stone, unit: $si$).
- The second line contains ten data points $a_1 ... a_{10}$ (the market prices of Seth Stones from $1si$ to $10si$, unit: yuan).

## Output Format

The output contains one line with a single integer, representing the maximum total profit.

## Sample Input and Output

### Sample Input #1

```
11
1 6 11 17 23 27 33 35 38 43
```

### Sample Output #1

```
32
```

### Sample Input #2

```
7
1 5 14 18 20 28 31 34 39 42
```

### Sample Output #2

```
21
```

## Notes

### Sample 1 Explanation:

Merge $11$ units of Seth Stone into one $4si$ Seth Stone and one $7si$ Seth Stone, and rent two boats with carrying capacities of $4si$ and $7si$, respectively. This is the optimal scheme, resulting in a maximum total profit of $32$ yuan.

### Attention:

- For all input data, the values are within the interval $(0, 100000)$ and are integers.
- Ensure the seller's maximum total profit is positive.
- Within the same line, each pair of data points is separated by a space.

The post-competition enhanced version was completed on October 13, 2020, at 19:18.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
