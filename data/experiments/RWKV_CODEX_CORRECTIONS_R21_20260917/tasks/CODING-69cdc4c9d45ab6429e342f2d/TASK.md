Problem

There is a puzzle game where you move curling stones and stack them exactly on the goal square. The detailed rules are as follows.

The field consists of H × W squares, with stones placed in some squares at the beginning. There is only one goal square, and no stone is placed on the goal square from the beginning. In addition, the field is surrounded by an outer wall, so stones will not jump out of the field on the way.

Players can choose one stone for each move and launch it in either the up, down, left, or right direction to slide it. A slipping stone will continue to slide until it hits another stone or the outer wall of the field. If it hits another stone, the stone on the hit side will be recoiled and will slide in a chain in the same direction as the first shot.

For example, when stone A is launched to the right in the state of FIG. 1, the final state is as shown in FIG.

Figure 1


Figure 1





Figure 2


Figure 2





The condition for clearing this puzzle is to place one of the stones on the field exactly on the goal square. It will not be cleared if you pass the goal square.

Your job is to create a program that takes the initial state of the field as
input and outputs whether the puzzle is clear or not.

Constraints

* 1 ≤ H ≤ 16
* 1 ≤ W ≤ 16
* 2 ≤ H x W ≤ 256
* Guaranteed to have only one goal square
* Guaranteed to have at least one square with curling stones on it

Input

The input is given in the following format.


H W
F11 F12 ... F1W
F21 F22 ... F2W
...
FH1 FH2 ... FHW


Fij is either'.',' O', or'@', and each has the following meaning. (1 ≤ i ≤ H, 1 ≤ j ≤ W)

*'.': Blank cell
*'o': The square on which the curling stone is placed
*'@': Goal square

Output

Print "yes" or "no" (not including "") on one line to see if the puzzle is clear.

Examples

Input

1 10
o........@


Output

yes


Input

3 6
......
.o..@.
......


Output

no


Input

6 4
....
.oo.
.oo.
....
.@..
....


Output

yes

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
