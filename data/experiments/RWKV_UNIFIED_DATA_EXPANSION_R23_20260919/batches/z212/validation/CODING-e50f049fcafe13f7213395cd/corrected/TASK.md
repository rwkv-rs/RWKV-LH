#### Problem Description:
There is a block-elimination game played on a 10x15 grid. The blocks come in three colors: red, green, and blue. You can remove a connected group of blocks of the same color if it has a size of 2 or more. Once removed, blocks will first drop down and then shift left, as illustrated in the given diagram.

The main objective of this game is to remove as many blocks as possible. The scoring method is as follows: whenever you remove a connected group containing m blocks, you score (m-2)^2 points. If you remove all blocks, you receive an additional 1000 points. Your task is to simulate playing this game.

Assume that an expert player will always remove the largest possible block, clicking the leftmost block, and if tied, the bottommost block.

#### Input Format:
The first line of input contains a number T, the number of test cases. The following T groups of data each contain a 10x15 matrix composed of 'R', 'G', 'B'. There is a blank line between two test groups.

#### Output Format
For each test case, output the label ‘ _Game x:_  ’.
After a blank line, output the sequence of moves, each in the format: _Move x at ( r,c ): removed b balls of color C, got s points._ , where X is the move number, r, c is the position, b is the number of blocks removed, c is the color of the blocks removed, and s is the score obtained. At the end of each test case, summarize with _Final score: s, with b balls remaining._ , where s is the total score and b is the number of blocks remaining. There is a blank line between two test cases.

## Input and Output Example

### Input Example #1

```
3
RGGBBGGRBRRGGBG
RBGRBGRBGRBGRBG
RRRRGBBBRGGRBBB
GGRGBGGBRRGGGBG
GBGGRRRRRBGGRRR
BBBBBBBBBBBBBBB
BBBBBBBBBBBBBBB
RRRRRRRRRRRRRRR
RRRRRRGGGGRRRRR
GGGGGGGGGGGGGGG
RRRRRRRRRRRRRRR
RRRRRRRRRRRRRRR
GGGGGGGGGGGGGGG
GGGGGGGGGGGGGGG
BBBBBBBBBBBBBBB
BBBBBBBBBBBBBBB
RRRRRRRRRRRRRRR
RRRRRRRRRRRRRRR
GGGGGGGGGGGGGGG
GGGGGGGGGGGGGGG
RBGRBGRBGRBGRBG
BGRBGRBGRBGRBGR
GRBGRBGRBGRBGRB
RBGRBGRBGRBGRBG
BGRBGRBGRBGRBGR
GRBGRBGRBGRBGRB
RBGRBGRBGRBGRBG
BGRBGRBGRBGRBGR
GRBGRBGRBGRBGRB
RBGRBGRBGRBGRBG
```

### Output Example #1

```
Game 1:
Move 1 at (4,1): removed 32 balls of color B, got 900 points.
Move 2 at (2,1): removed 39 balls of color R, got 1369 points.
Move 3 at (1,1): removed 37 balls of color G, got 1225 points.
Move 4 at (3,4): removed 11 balls of color B, got 81 points.
Move 5 at (1,1): removed 8 balls of color R, got 36 points.
Move 6 at (2,1): removed 6 balls of color G, got 16 points.
Move 7 at (1,6): removed 6 balls of color B, got 16 points.
Move 8 at (1,2): removed 5 balls of color R, got 9 points.
Move 9 at (1,2): removed 5 balls of color G, got 9 points.
Final score: 3661, with 1 balls remaining.
Game 2:
Move 1 at (1,1): removed 30 balls of color G, got 784 points.
Move 2 at (1,1): removed 30 balls of color R, got 784 points.
Move 3 at (1,1): removed 30 balls of color B, got 784 points.
Move 4 at (1,1): removed 30 balls of color G, got 784 points.
Move 5 at (1,1): removed 30 balls of color R, got 784 points.
Final score: 4920, with 0 balls remaining.
Game 3:
Final score: 0, with 150 balls remaining.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
