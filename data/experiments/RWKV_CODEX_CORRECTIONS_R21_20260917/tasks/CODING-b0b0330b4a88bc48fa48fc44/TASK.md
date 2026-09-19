There are $n$ robots arranged in a circle, numbered in counterclockwise order from $0$ to $n-1$.

Each robot has two hands. The robot numbered $i$ initially points its "left hand" to the robot numbered $l_i$ and its "right hand" to the robot numbered $r_i$.

All robots contain $m$ lines of "instructions". Instructions come in two types: "basic instructions" and "advanced instructions". The advanced instructions are more complex, but they fundamentally serve the same purpose. Below are the formats of these instructions and their effects when "executed". The term "self" refers to the robot that owns the instruction.

### Instructions

#### Basic Instructions

- `SLACKOFF`: **"Slack off"**, meaning do nothing.
- `MOVE h z`: Move the $h$-th hand counterclockwise by $z$ robot positions. When $h=0$, it refers to the "left hand"; when $h=1$, it refers to the "right hand".
- `SWAP h x y`: Swap the $x$-th line of instructions of the robot pointed to by the $h$-th hand with the $y$-th line of instructions of self.
- `MIRROR h x`: "Mirror" the $x$-th line of instructions of the robot pointed to by the $h$-th hand, inverting $h$ (changing $0$ to $1$ and $1$ to $0$). This has no effect on `SLACKOFF` instructions; for `TRIGGER` instructions, it modifies the $h$ in the instruction that gets executed upon triggering.
- `REPLACE h x <COMMAND>`: Replace the $x$-th line of instructions of the robot pointed to by the $h$-th hand with `<COMMAND>`, where `<COMMAND>` is a complete instruction.

#### Advanced Instructions

- `ACTIVATE h`: **"Activate"** the robot pointed to by the $h$-th hand, executing all its instructions in order. The next instruction is executed only after the previous one completes. Note that instructions may change during execution, and the updated instructions should be executed. The `ACTIVATE` instruction completes only after all instructions of the targeted robot are executed.
- `TRIGGER <COMMANDNAME>: <COMMAND>`: `<COMMANDNAME>` is the name of the instruction, the first all-uppercase word in the instruction; `<COMMAND>` is a complete basic instruction. `TRIGGER` instructions are not executed directly but are skipped during execution. However, when another robot finishes executing an instruction and its "right hand" points to self, the earliest `TRIGGER` instruction that matches the condition (if any) is **"triggered"**—executing the corresponding `<COMMAND>`. The condition is:
  - If `<COMMANDNAME>` is not `TRIGGER`, the last executed instruction was `<COMMANDNAME>`;
  - If `<COMMANDNAME>` is `TRIGGER`, the last executed instruction was the one triggered by the `TRIGGER` instruction.

You need to start from robot $0$ and activate these robots in order, looping around, and output information about the first $k$ instructions executed.

## Input Format

The first line contains three positive integers $n, m, k$.

The next sections describe the $n$ robots in ascending order of their numbers.

For each robot, the first line contains two non-negative integers $l_i, r_i$, indicating the robot numbers pointed to by the "left hand" and "right hand", respectively.

The next $m$ lines, in order, describe the robot's instructions, formatted as described in the problem.

## Output Format

Output $k$ lines, describing the first $k$ instructions to be executed, output before execution, one per line, as follows:

- For "slacking off": `Robot <id> slacks off.`
- For "moving": `Robot <id> moves its <side> hand towards Robot <id2>.`
- For "swapping": `Robot <id> swaps a line of command with Robot <id2>.`
- For "mirroring": `Robot <id> modifies a line of command of Robot <id2>.`
- For "replacing": `Robot <id> replaces a line of command of Robot <id2>.`
- For "activating" (different from the overall activation): `Robot <id> activates Robot <id2>.`
- `TRIGGER` instructions do not need output, but when triggered, output the corresponding basic instruction execution information as above.

## Sample Input and Output

### Sample Input #1

```
2 2 5
0 0
MOVE 1 1
MOVE 0 1
0 1
TRIGGER MOVE: MOVE 0 1
SLACKOFF
```

### Sample Output #1

```
Robot 0 moves its right hand towards Robot 1.
Robot 1 moves its left hand towards Robot 1.
Robot 0 moves its left hand towards Robot 1.
Robot 1 moves its left hand towards Robot 0.
Robot 1 slacks off.
```

### Sample Input #2

```
2 2 4
0 1
ACTIVATE 1
SLACKOFF
0 1
SWAP 0 2 2
MIRROR 0 1
```

### Sample Output #2

```
Robot 0 activates Robot 1.
Robot 1 swaps a line of command with Robot 0.
Robot 1 slacks off.
Robot 0 modifies a line of command of Robot 0.
```

### Sample Input #3

```
3 2 6
1 2
ACTIVATE 0
ACTIVATE 0
2 1
SWAP 0 2 2
TRIGGER ACTIVATE: REPLACE 0 2 SLACKOFF
0 1
TRIGGER MIRROR: SLACKOFF
SLACKOFF
```

### Sample Output #3

```
Robot 0 activates Robot 1.
Robot 1 swaps a line of command with Robot 2.
Robot 1 slacks off.
Robot 2 replaces a line of command of Robot 0.
Robot 0 slacks off.
Robot 1 swaps a line of command with Robot 2.
```

### Sample Input #4

```
3 2 8
0 1
SLACKOFF
TRIGGER MOVE: SLACKOFF
1 2
TRIGGER TRIGGER: SLACKOFF
TRIGGER SLACKOFF: MOVE 0 1
2 0
TRIGGER SLACKOFF: MOVE 1 2
TRIGGER TRIGGER: MOVE 1 1
```

### Sample Output #4

```
Robot 0 slacks off.
Robot 1 moves its left hand towards Robot 2.
Robot 2 moves its right hand towards Robot 1.
Robot 1 slacks off.
Robot 2 moves its right hand towards Robot 0.
Robot 0 slacks off.
Robot 1 slacks off.
Robot 2 moves its right hand towards Robot 2.
```

### Sample Input #5

See the attached file `5.in`.

### Sample Output #5

See the attached file `5.ans`.

## Notes/Hints

### Sample #1 Explanation

The triggering of `TRIGGER` instructions happens after the execution of another instruction. Note that a `TRIGGER` instruction cannot trigger itself.

### Sample #2 Explanation

Instructions may change during execution of previous instructions; the updated instructions should be executed.

### Sample #3 Explanation

The `ACTIVATE` instruction completes only after all instructions of the targeted robot are executed.

### Sample #4 Explanation

Only the earliest `TRIGGER` instruction that meets the condition is triggered.

### Sample #5 Explanation

Generous donation? Strong assistance?

### Subtasks

- All instructions are guaranteed to be correctly formatted.
- The input file length does not exceed $5\mathtt{MB}$.
- At least $k$ instructions can be executed.
- Constraints: $2 \le n \le 100$, $1 \le m \le 10$, $1 \le k \le 3 \times 10^5$.
- $0 \le l_i, r_i < n$.
- $0 \le h \le 1$, $1 \le x, y \le m$, $1 \le z < n$. All input numbers are integers.

### Usage Agreement

From THUPC2024 (2024 Tsinghua University Student Programming Contest and University Invitational Tournament) Preliminary.

1. Any organization or individual may freely use or republish the problems from this repository.
2. When using these problems, the organization or individual must ensure that they are free and publicly accessible, prohibiting any form of profit-making or special privileges.
3. If possible, please provide access to data, standard solutions, problem explanations, etc., when using these problems; otherwise, please include the GitHub address of this repository.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
