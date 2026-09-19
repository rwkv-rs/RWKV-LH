You are given an arrow maze where at each intersection, if you enter from a specific direction, there is a set of arrows on the ground pointing near your direction. The arrows can point left, forward, right, or any combination thereof.

When you enter an intersection from a certain direction, you can only proceed in a direction marked by one of the arrows relative to your entry direction. At the starting point, you may choose any direction.

Given a start and an end point, find the shortest path between them.

Each edge has a length of 1.

## Input and Output Example

### Input Example #1

```
SAMPLE
3 1 N 3 3
1 1 WL NR *
1 2 WLF NR ER *
1 3 NL ER *
2 1 SL WR NF *
2 2 SL WF ELF *
2 3 SFR EL *
0
NOSOLUTION
3 1 N 3 2
1 1 WL NR *
1 2 NL ER *
2 1 SL WR NFR *
2 2 SR EL *
0
END
Figure 1: An Example Walk-Through
Arrow Maz
```

### Output Example #1

```
SAMPLE
(3,1) (2,1) (1,1) (1,2) (2,2) (2,3) (1,3) (1,2) (1,1) (2,1) 
(2,2) (1,2) (1,3) (2,3) (3,3)
NOSOLUTION
No Solution Possible
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
