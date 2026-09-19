Cow Bessie has been abducted by aliens and is now held captive in an alien spaceship! The spaceship has $N$ ($1 \leq N \leq 60$) rooms numbered $1 \ldots N$, with some rooms connected by one-way doors (due to strange alien technology, a door might even connect a room to itself!). However, no two doors have the same starting and ending rooms. Additionally, Bessie has a remote control with buttons numbered $1 \ldots K$ ($1 \leq K \leq 60$).

If Bessie can complete a peculiar task, the aliens will release her. First, they will choose two rooms $s$ and $t$ ($1 \leq s, t \leq N$), and two integers $b_s$ and $b_t$ ($1 \leq b_s, b_t \leq K$). They will place Bessie in room $s$ and make her press button $b_s$ immediately. Then, Bessie needs to continue navigating the spaceship while pressing buttons. There are some rules she must follow:

- In each room, after pressing exactly one button, she must choose to leave through a door to another room (possibly the same room) or stop her actions.
- Once Bessie presses a button, pressing it again becomes illegal unless she has pressed a button with a higher number in between. In other words, pressing a button with number $x$ makes that button illegal and resets all buttons with numbers $< x$ to be legal.
- If Bessie presses an illegal button, the task fails, and the aliens will imprison her.

Bessie will only be released if she stops in room $t$, the last button she pressed is $b_t$, and she has not pressed any illegal buttons.

Bessie is worried she might not be able to complete this task. For $Q$ ($1 \leq Q \leq 60$) queries, each containing a set of possible $s, t, b_s$, and $b_t$ that Bessie thinks might be chosen, she wants to know the number of valid sequences of room visits and button presses that will release her. Since the answer may be very large, output it modulo $10^9 + 7$.

## Input Format

The first line of input contains $N, K, Q$.

The next $N$ lines each contain $N$ binary digits (0 or 1). If there is a door from room $i$ to room $j$, the $j$-th digit of the $i$-th line is 1; otherwise, it is 0.

The next $Q$ lines each contain four integers $b_s, s, b_t, t$, representing the starting button, starting room, ending button, and ending room, respectively.

## Output Format

For each of the $Q$ queries, output the number of valid sequences modulo $10^9 + 7$ on a single line.

## Sample Input and Output

### Input Sample #1

```
6 3 8
010000
001000
000100
000010
000000
000001
1 1 1 1
3 3 1 1
1 1 3 3
1 1 1 5
2 1 1 5
1 1 2 5
3 1 3 5
2 6 2 6
```

### Output Sample #1

```
1
0
1
3
2
2
0
5
```

### Input Sample #2

```
6 4 6
001100
001110
101101
010111
110111
000111
3 2 4 3
3 1 4 4
3 4 4 1
3 3 4 3
3 6 4 3
3 1 4 2
```

### Output Sample #2

```
26
49
29
27
18
22
```

### Input Sample #3

```
6 10 5
110101
011001
001111
101111
111010
000001
2 5 2 5
6 1 5 2
3 4 8 3
9 3 3 5
5 1 3 4
```

### Output Sample #3

```
713313311
716721076
782223918
335511486
539247783
```

## Notes/Hints

The doors connect rooms $1 \rightarrow 2$, $2 \rightarrow 3$, $3 \rightarrow 4$, $4 \rightarrow 5$, and $6 \rightarrow 6$.

For the first query, Bessie must stop immediately after pressing the first button.

For the second query, the answer is obviously zero since it's impossible to go from room 3 to room 1.

For the third query, Bessie's only choice is to move from room 1 to room 2 to room 3, pressing buttons 1, 2, and 3.

For the fourth query, Bessie's movement is unique, and she has three possible sequences of button presses:

- (1,2,3,2,1)
- (1,2,1,3,1)
- (1,3,1,2,1)

For the last query, Bessie has five possible sequences of button presses:

- (2)
- (2,3,2)
- (2,3,1,2)
- (2,1,3,2)
- (2,1,3,1,2)

### Test Case Properties:

- In test cases 4-7, $K \leq 5$ and $(b_s, s)$ are the same for all queries.
- In test cases 8-11, $b_s = K - 1$ and $b_t = K$ for all queries.
- In test cases 12-15, $N, K, Q \leq 20$.
- In test cases 16-23, there are no additional restrictions.

Problem authored by Benjamin Qi.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
