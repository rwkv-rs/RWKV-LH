Gennady and Georgiy are playing a game on a directed graph. The graph has $n$ vertices and $m$ edges, and loops are allowed. Gennady and Georgiy have a token placed on one of the graph vertices. Players take turns moving the token along one of the edges that starts at the vertex where the token is currently located. When there is no such edge, the player loses the game.

For each initial position of the token and the player who moves first, your task is to determine the outcome of the game. Does it seem easy? Not quite.

On one side, Gennady is having a lot of fun playing this game, so he wants to play as long as possible. He even prefers a strategy that leads to an infinite game over a strategy that makes him the winner. But if he cannot make the game infinite, then he obviously prefers winning to losing.

On the other side, Georgiy has a lot of other work, so he does not want to play the game infinitely. Georgiy wants to win the game, but if he cannot win, then he prefers losing over making the game infinite.

Both players are playing optimally. Both players know the preferences of the other player.

### Input Format

The first line contains two integers $n$ and $m$ representing the number of vertices and edges, respectively. The next $m$ lines each contain two integers $a$ and $b$, denoting an edge from vertex $a$ to vertex $b$. Vertices are numbered from $1$ to $n$. Each $(a, b)$ pair appears at most once.

### Output Format

Print two lines. The first line should contain $n$ characters, where the $i$-th character denotes the outcome of the game if Gennady starts at vertex $i$. The second line should contain $n$ characters, where the $i$-th character denotes the outcome of the game if Georgiy starts at vertex $i$. The outcome of the game is denoted by `W` if the starting player wins, `L` if the starting player loses, and `D` (draw) if the game runs infinitely.

## Sample Input and Output

### Input Sample #1

```
6 7
1 2
2 1
2 3
1 4
4 1
4 5
5 6
```

### Output Sample #1

```
WDLDWL
DWLLWL
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 512 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
