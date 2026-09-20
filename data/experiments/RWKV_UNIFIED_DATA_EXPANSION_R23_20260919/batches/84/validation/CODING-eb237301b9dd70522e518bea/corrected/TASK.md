A renowned thief enters a storage room filled with gems, which consists of a series of rooms numbered starting from $0$. To enter the $i$-th room, one must pass through the $(i-1)$-th room, as illustrated in the figure below:

![](https://cdn.luogu.com.cn/upload/pic/6100.png)

## Problem Description

The figure above shows three rooms, with the black parts representing doors connecting the rooms, numbered from left to right as $0, 1, 2, \cdots$. It is known that when the thief enters the storage room through the $0$-th door, the timing system starts. Each door has its own closing time. Each room contains different types of gems, with each type having a different value and time required for the thief to take it. To simplify the problem, we assume that the time taken to move between rooms is negligible, and the quantity of each type of gem in every room is unlimited. The question is, what is the maximum value of gems the thief can obtain while successfully escaping?

Note: For each door, the thief must exit strictly before the door closes.

## Input Format

The first line of each test case contains two integers $N$ and $M$, representing the number of rooms in the storage room and the number of types of gems, respectively. The second line contains $N$ positive integers, each indicating the closing time of the $i$-th door (door numbering starts from $0$). The following $M$ lines each contain three integers $r, v$, and $t$, representing the room number $r$ where the gem is located, its value $v$, and the time $t$ required for the thief to take it.

## Output Format

Output the maximum value of gems the thief can obtain while successfully escaping the storage room.

## Sample Input and Output

### Input Sample #1

```
3 4
9 5 5
0 1 2
1 2 2
2 3 2
2 5 3
```

### Output Sample #1

```
8
```

## Notes/Hints

### Sample Explanation

Although the gem worth $5$ in the $2$-nd room is valuable, it is better to take two gems worth $3$ each and two gems worth $1$ each from the $0$-th room, totaling $8$ in value.

### Data Range and Constraints

For $100\%$ of the data, the number of rooms does not exceed $50$, the closing time of each door does not exceed $1000$, and the number of types of gems does not exceed $100$, with each gem's value not exceeding $1000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
