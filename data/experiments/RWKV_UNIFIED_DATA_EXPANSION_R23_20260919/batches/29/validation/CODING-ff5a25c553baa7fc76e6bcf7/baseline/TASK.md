Hemisphere Network is the largest television network in Tumbolia, a small country located east of South America (or south of East America). The most popular sport in Tumbolia, unsurprisingly, is soccer; many games are broadcast every week in Tumbolia.

 Hemisphere Network receives many requests to replay dubious plays; usually, these happen when a player is deemed to be offside by the referee. An attacking player is _offside_ if he is nearer to his opponents’ goal line than the second last opponent. A player is not offside if

- he is level with the second last opponent or
- he is level with the last two opponents.

 Through the use of computer graphics technology, Hemisphere Network can take an image of the field and determine the distances of the players to the defending team’s goal line, but they still need a program that, given these distances, decides whether a player is offside.

## Input Format

The input file contains several test cases. The first line of each test case contains two integers A and D separated by a single space indicating, respectively, the number of attacking and defending players involved in the play (2 <= A,D <= 11). The next line contains A integers B $ _{i} $ separated by single spaces, indicating the distances of the attacking players to the goal line (1 <= B $ _{i} $ <= 10 $ ^{4} $ ). The next line contains D integers C $ _{j} $ separated by single spaces, indicating the distances of the defending players to the goal line (1 <= C $ _{j} $ <= 10 $ ^{4} $ ). The end of input is indicated by A = D = 0.

## Output Format

For each test case in the input print a line containing a single character: “Y” (uppercase) if there is an attacking player offside, and “N” (uppercase) otherwise.

## Sample Input and Output

### Sample Input #1

```
2 3
500 700
700 500 500
2 2
200 400
200 1000
3 4
530 510 490
480 470 50 310
0 0
```

### Sample Output #1

```
N
Y
N
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
