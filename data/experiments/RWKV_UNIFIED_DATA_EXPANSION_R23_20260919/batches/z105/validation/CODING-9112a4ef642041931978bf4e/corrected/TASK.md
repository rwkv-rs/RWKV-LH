Otaku JYY loves playing RPG games, such as Sword and Fairy, Xuanyuan Sword, etc. However, what JYY enjoys is not the battle scenes but the melodramatic storylines similar to TV dramas. These games often have many subplot stories. Now, JYY wants to spend the least amount of time watching all the subplot stories.

## Problem Description

In the RPG game JYY is currently playing, there are $N$ plot points numbered from $1$ to $N$. The $i$-th plot point can lead to $K_i$ different new plot points based on JYY's choices. If $K_i$ is $0$, it means that the $i$-th plot point is the end of the game.

JYY needs a certain amount of time to watch a subplot story. JYY starts at the $1$-st plot point, which is the beginning of the game. Clearly, any plot point is reachable from the $1$-st plot point. Additionally, the game progresses in an irreversible manner, ensuring that no plot point can be revisited once left. Due to JYY's excessive use of cheats, the game's "save" and "load" functions are damaged.

Therefore, the only way for JYY to return to a previous plot point is to exit the current game and start a new one, which means going back to the $1$-st plot point. JYY can exit and restart the game at any time. Repeatedly starting new games to watch already seen stories is painful, so JYY wants to spend the least amount of time watching all different subplot stories.

## Input Format

The input consists of a single line containing a positive integer $N$.

The next $N$ lines each describe the information for the $i$-th plot point:

The first integer is $K_i$, followed by $K_i$ pairs of integers, $b_{i,j}$ and $t_{i,j}$, indicating that from plot point $i$, one can go to plot point $b_{i,j}$, and watching this subplot story takes $t_{i,j}$ time.

## Output Format

Output a single line containing an integer, which is the minimum time JYY needs to watch all subplot stories.

## Sample Input and Output

### Input Sample #1

```
6
2 2 1 3 2
2 4 3 5 4
2 5 5 6 6
0
0
0
```

### Output Sample #1

```
24
```

## Notes

### Sample Explanation

JYY needs to restart the game 3 times, plus the initial start, making a total of 4 game sessions:

- $1 \to 2 \to 4$;
- $1 \to 2 \to 5$;
- $1 \to 3 \to 5$;
- $1 \to 3 \to 6$.

For $100\%$ of the data, $N \le 300$, $0 \le K_i \le 50$, $1 \le t_{i,j} \le 300$, and $\sum K_i \le 5000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
