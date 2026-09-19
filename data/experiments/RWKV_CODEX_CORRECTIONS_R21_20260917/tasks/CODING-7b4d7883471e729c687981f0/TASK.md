Polycarp decided to generate a biome map for his game. A map is a matrix divided into cells $$$1 \times 1$$$. Each cell of the map must contain one of the available biomes.

Each biome is defined by two parameters: temperature (an integer from $$$1$$$ to $$$n$$$) and humidity (an integer from $$$1$$$ to $$$m$$$). But not for every temperature/humidity combination, a corresponding biome is available.

The biome map should be generated according to the following rules:

- each cell of the map belongs to exactly one biome;
- each available biome has at least one cell on the map;
- if two cells of the map are adjacent by the side and they belong to biomes with parameters ($$$t_1, h_1$$$) and ($$$t_2, h_2$$$), respectively, then the equality $$$|t_1-t_2| + |h_1-h_2| = 1$$$ holds;
- let the number of available biomes be equal to $$$k$$$, then the number of rows and columns of the map (separately) should not exceed $$$k$$$.

Help Polycarp generate a biome map that meets all the conditions described above (or report that this is impossible).

Input

The first line contains a single integer $$$t$$$ ($$$1 \le t \le 20$$$) — the number of test cases.

The first line of each test case contains two integers $$$n$$$ and $$$m$$$ ($$$1 \le n, m \le 10$$$) — maximum temperature and humidity parameters.

The following $$$n$$$ lines contain $$$m$$$ integers each $$$a_{i,1}, a_{i, 2}, \dots, a_{i, m}$$$ ($$$0 \le a_{i, j} \le 100$$$), where $$$a_{i, j}$$$ — the biome identifier with the parameters $$$(i, j)$$$, if $$$a_{i, j} \neq 0$$$, otherwise the biome with such parameters is not available.

All biome identifiers are different, and there are at least two biomes available.

Output

For each test case, print the answer in the following format:

- print $$$-1$$$ in a single line if there is no map that meets all the conditions;
- otherwise, in the first line, print two integers $$$h$$$ and $$$w$$$ — the number of rows and columns of the map, respectively. In the following $$$h$$$ lines, print $$$w$$$ integers — the identifiers of the biomes in the corresponding cells of the map.

Examples

Input

4
2 3
0 2 5
0 1 0
3 5
0 3 4 9 11
1 5 0 10 12
0 6 7 0 0
2 2
2 0
0 5
1 2
13 37

Output

1 3
5 2 1 
2 8
11 9 4 3 5 1 5 6 
12 10 9 4 3 5 6 7 
-1
1 2
13 37

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
