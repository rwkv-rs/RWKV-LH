In the world of Travian, various tribes live, with the most powerful being the Romans, Gauls, and Germans. They have engaged in countless battles for resources and land, giving rise to many renowned heroes and moving stories.

Among these tribes, there are roads connecting them, which are crucial hubs in the world of Travian. For simplicity, you can consider these interconnected roads as a tree, highlighting the importance of each road. These roads allow builders to conduct friendly diplomacy.

However, due to resource scarcity, neighboring tribes (connected by a road) often experience conflicts, sometimes escalating into large-scale wars. To avoid collateral damage, roads between tribes engaged in large-scale wars are closed off, and some powerful tribes can even be at war with multiple neighbors, making those roads impassable.

After bitter battles, tribes may sign a truce (temporarily cease hostilities, potentially resuming later), allowing the road between them to reopen, enabling builders to pass through and acquire new designs to strengthen their tribes.

For simplicity, all war events are numbered in the order they occur (the first war is numbered 1, the second is 2, and so on). When a truce is declared, the war's number is provided, and that war is recorded in history, no longer affecting other war numbers.

Builders dislike wars because they may prevent travel between tribes for diplomatic purposes. Before setting out, they inquire if they can reach their intended destination.

## Problem Description

You need to handle the following three types of events, all given in chronological order:

1. `Q p q` - A builder from tribe $p$ wants to know if they can reach tribe $q$. You must answer `Yes` or `No`, paying attention to case sensitivity.

2. `C p q` - Tribes $p$ and $q$ go to war. Ensure they are adjacent and currently at peace.

3. `U x` - The $x$-th war ends, permanently recorded in history (this message will not be repeated).

## Input Format

The first line contains two numbers $n$ and $m$, representing the number of tribes and the total number of events, respectively.

The next $n - 1$ lines each contain two numbers $p$ and $q$, indicating a road connecting tribe $p$ and tribe $q$.

The next $m$ lines describe each event as per the problem description.

## Output Format

For each `Q` event, output a line containing `Yes` or `No`, indicating whether a builder can travel from tribe $p$ to tribe $q$.

## Sample Input and Output

### Input Sample #1

```
5 9
1 2
2 3
3 4
4 5
Q 1 4
C 2 1
C 4 3
Q 3 1
Q 1 5
U 1
U 2
C 4 3
Q 3 4
```

### Output Sample #1

```
Yes
No
No
No
```

### Input Sample #2

```
10 10
1 2
1 3
3 4
3 5
1 6
3 7
1 8
2 9
5 10
C 8 1
Q 6 1
C 2 1
Q 2 10
U 1
C 9 2
C 7 3
U 3
Q 6 7
Q 1 10
```

### Output Sample #2

```
Yes
No
No
Yes
```

### Input Sample #3

```
20 20
1 2
1 3
2 4
1 5
1 6
4 7
1 8
2 9
5 10
1 11
2 12
7 13
1 14
1 15
11 16
4 17
3 18
18 19
8 20
Q 13 5
C 14 1
C 16 11
U 1
U 2
C 20 8
Q 7 1
C 7 4
Q 17 17
Q 1 6
C 16 11
C 2 1
Q 16 2
U 3
U 5
U 6
C 2 1
C 6 1
C 13 7
C 11 1
```

### Output Sample #3

```
Yes
Yes
Yes
Yes
No
```

## Notes/Hints

For 30% of the data, $n, m \leq 6 \times 10^3$.

For another 30% of the data, the geographical relationship between tribes is a chain, with a road between $i$ and $i + 1$.

For another 30% of the data, $n, m \leq 10^5$.

For 100% of the data, $1 \leq n, m \leq 3 \times 10^5$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
