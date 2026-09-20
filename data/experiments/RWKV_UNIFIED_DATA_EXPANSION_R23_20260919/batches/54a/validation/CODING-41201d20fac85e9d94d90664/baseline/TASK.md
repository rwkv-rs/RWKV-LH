### Problem Description

The area is surrounded by majestic mountains. However, there is a problem: climbing these mountains is very challenging due to significant elevation differences. To make mountaineering more accessible and enjoyable for more people, we wish to ease the climbing process.

To achieve this, we propose the following modification to the mountains: they consist of $n$ adjacent piles of stones, each with a height $h_i$. The height difference between adjacent piles is $h_{i+1} - h_i$ ($1 \le i \le n-1$). We want the absolute value of these height differences to be less than or equal to $d$.

We can achieve this by increasing or decreasing the height of each pile of stones. The height of the first pile (start point) and the last pile (end point) must remain unchanged. Since adding and removing stones requires considerable effort, we aim to minimize the total number of added and removed stones. What is this minimum value?

### Input

The first line contains a positive integer indicating the number of test cases, up to 100. Each test case contains:

• A line with two integers $n$ ($2 \le n \le 100$) and $d$ ($0 \le d \le 10^9$): the number of stone piles and the allowed maximum height difference.

• A line with $n$ integers $h_i$ ($0 \le h_i \le 10^9$): the height of the $i^{th}$ pile of stones.

### Output

For each test case:

• Output a single line with the minimum number of stones to be added and removed. If it is impossible to achieve the goal, output "impossible".

## Sample Input and Output

### Sample Input #1

```
3
10 2
4 5 10 6 6 9 4 7 9 8
3 1
6 4 0
4 2
3 0 6 3
```

### Sample Output #1

```
6
impossible
4
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
