This year, there are $ N $ participants in the Paken camp. Now, all members have arrived at the lecture venue. The slide is displayed on the screen at the far left. However, the venue is narrow, and the members have to line up in a single row from left to right. Each member is numbered from $ 1 $ to $ N $ in order from the left.

In this group, there is a culture of arranging members in order of their ratings from the closest to the slide, so they cannot change their positions. However, since the participants have various heights, some shorter members may not be able to see the screen.

Therefore, the magical boy Osmium_1008 decided to use a magic that can reduce the height of some members (Osmium_1008 can reduce the height through magic, but cannot increase it).

The height of member $ i $ is $ A_i $, and the happiness when they can see the slide is represented by $ B_i $. If there is someone taller than them (**same height is acceptable**) among the people to their left (with smaller numbers), that person cannot see the slide, and their happiness becomes $ 0 $.

Also, if Osmium_1008 uses magic, the happiness of the member whose height is reduced will be further reduced by the length of the reduction.

Find the maximum total happiness of all members. Note that Osmium_1008 may choose not to use magic at all. Also, the happiness value of each person can be negative.

## Input Format

The input is given from the standard input in the following format:

> $ N $  
> $ A_1 $ $ A_2 $ $ \ldots $ $ A_{N-1} $ $ A_N $  
> $ B_1 $ $ B_2 $ $ \ldots $ $ B_{N-1} $ $ B_N $

## Output Format

Output the maximum total happiness of all members in one line.

## Sample Input and Output

### Sample Input #1

```
4
40 60 20 10
25 30 80 50
```

### Sample Output #1

```
95
```

### Sample Input #2

```
5
112 76 50 35 22
15 60 40 120 90
```

### Sample Output #2

```
140
```

### Sample Input #3

```
5
151 162 155 161 170
4 8 23 10 15
```

### Sample Output #3

```
53
```

## Notes/Hints

### Constraints

- All inputs are integers.
- $ 1\leq\ N\leq\ 10^5 $
- $ 1\leq\ A_i,B_i\leq\ 10^9 $

### Subtasks

There are $ 2 $ subtasks for this problem:

1. (400 points) $ N\ \leq\ 5000 $
2. (600 points) No additional constraints.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
