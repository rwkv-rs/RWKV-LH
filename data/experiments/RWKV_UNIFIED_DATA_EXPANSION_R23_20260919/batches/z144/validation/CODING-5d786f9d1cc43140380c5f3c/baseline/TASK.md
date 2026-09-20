You are a programmer who loves pretty girl games (a sub-genre of dating simulation games). A game, which is titled "Floatable Heart" and was released last Friday, has arrived at your home just now. This game has multiple stories. When you complete all of those stories, you can get a special figure of the main heroine, Megumi. So, you want to hurry to play the game! But, let's calm down a bit and think how to complete all of the stories in the shortest time first.

In fact, you have the special skill that allows you to know the structure of branching points of games. By using the skill, you have found out that there are n branching points in this game and i-th branching point has k_{i} choices. This game is so complicated that multiple routes get to i-th branching point probably. You also noticed that it takes c_{ij} minutes to proceed from i-th branching point to another branching point (or an ending), if you select j-th choice of i-th branching point. Of course you need to select all the choices on all the branching points and read stories between a branching point and another branching point (or an ending) to complete all of those stories. In addition, you can assume it only takes negligible time to return to the beginning of the game ("reset") and to play from the beginning to the first branching point.

The game's manual says that this game has an additional feature called "Quick Save", and the feature allows you to record the point where you are currently playing and return there at any time later. However, this feature is not working for some bug. Thus you have to restart from the first branching point every time, if you reach an ending or quit the game on the way. Any patch to fix this bug has not been yet published. This is an imposed tribulation for the fastest players.

Well, let's estimate how long it will take for completing all of the stories in the shortest time.

Input

A data set is given in the following format.


n
k_{1} t_{11} c_{12} ... t_{1k_{1}} c_{1k_{1}}
:
:
k_{n} t_{n1} c_{n2} ... t_{nk_{n}} c_{nk_{n}}


The first line of the data set contains one integer n (2 \leq n \leq 1{,}000), which denotes the number of the branching points in this game. The following n lines describe the branching points. The i-th line describes the branching point of ID number i. The first integer k_{i} (0 \leq k_{i} \leq 50) is the number of choices at the i-th branching point. k_{i} ≥ 0 means that the i-th branching point is an ending. Next 2k_{i} integers t_{ij} (1 \leq t_{ij} \leq n) and c_{ij} (0 \leq c_{ij} \leq 300) are the information of choices. t_{ij} denotes the ID numbers of the next branching points when you select the j-th choice. c_{ij} denotes the time to read the story between the i-th branching point and the t_{ij}-th branching point. The branching point with ID 1 is the first branching point. You may assume all the branching point and endings are reachable from the first branching point. You may also assume that there is no loop in the game, that is, no branching point can be reached more than once without a reset.

Output

Print the shortest time in a line.

Sample Input 1


2
1 2 2
0


Output for the Sample Input 1


2


Sample Input 2


6
2 2 1 3 2
2 4 3 5 4
2 5 5 6 6
0
0
0


Output for the Sample Input 2


24


Sample Input 3


6
3 2 100 3 10 3 10
1 4 100
1 4 10
3 5 1 5 1 6 1
0
0


Output for the Sample Input 3


243






Example

Input

2
1 2 2
0


Output

2

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
