Little R is playing a war game. The game map is a matrix of M rows and N columns, where each cell can either be an obstacle or an open space. At the beginning of the game, several enemy troops are scattered across different open space cells. Each troop can move from its current cell to one of the four adjacent cells, but cannot move into cells containing obstacles. If a troop moves out of the map boundaries, the game is lost.

## Problem Description

Your task is to, before the enemy troops start moving, use aerial bombing to make certain open space cells impassable, potentially preventing the enemy from moving out of the map boundaries (for a specific reason, you cannot directly bomb the cells where the enemy troops are located). Due to varying terrain, the amount of explosives needed to make each open space cell impassable may differ. You need to calculate the minimum amount of explosives required to block the enemy.

## Input Format

The first line of the input file contains two numbers, M and N, representing the length and width of the matrix, respectively. The next M lines each contain N numbers separated by spaces, where each number represents the status of a cell: if the number is -1, the cell is an obstacle; if the number is 0, the cell contains an enemy troop; if the number is a positive integer x, the cell is an open space and the amount of explosives needed to make it impassable is x.

The number of enemy troops is not 1, meaning there are multiple 0s on the map.

## Output Format

Output a single number representing the minimum amount of explosives needed. The data guarantees that a solution exists.

## Sample Input and Output

### Input Sample #1

```
4 3
1 2 1
1 10 1
1 0 -1
1 1 1
```

### Output Sample #1

```
6
```

## Notes

For 50% of the data, 1 ≤ M,N ≤ 10.

For 100% of the data, 1 ≤ M,N ≤ 30.

Each number in the matrix does not exceed 100.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
