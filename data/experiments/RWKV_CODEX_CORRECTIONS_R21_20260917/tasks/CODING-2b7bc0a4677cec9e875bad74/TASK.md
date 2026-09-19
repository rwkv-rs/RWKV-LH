define is designing an amusement park called "Paken Land" which will open in April. This amusement park is characterized by its long and narrow shape in the east-west direction, with the entrance located at the westernmost point. Hereafter, we will refer to the place $ k $ meters east of the entrance as location $ k $.

There are $ N $ attractions in this amusement park, numbered $ 1, 2, \dots, N $. Attraction $ i $ is located at location $ i $.

define has invited Penguin to the opening day of Paken Land. Penguin takes 1 second to move 1 meter. Penguin has planned to ride attractions $ M $ times, deciding that the $ i $-th attraction to ride will be attraction $ A_i $. In this plan, the shortest time to move from location $ A_i $ to location $ A_{i+1} $ is $ T_i $ seconds, and the total time for moving is $ \sum_{i=1}^{M-1}{T_i} $ seconds.

However, just before the opening, define started thinking, "Wouldn't it be difficult to move if the attractions are lined up in a row?" If this continues, Penguin might get tired of moving and go home. Therefore, due to the lack of time, define decided to build only one warp road. By choosing two locations to build a warp road, it becomes possible to move between these two locations in 1 second in both directions.

You are given $ Q $ queries. The $ i $-th query asks, "What is the travel time for Penguin's plan if a warp road is built between location $ S_i $ and location $ T_i $?" Answer each query.

## Input Format

The input is given from the standard input in the following format. All inputs are integers.

> $ N\ M $ $ A_1\ A_2\ \dots\ A_M $ $ Q $ $ S_1\ T_1 $ $ \vdots $ $ S_Q\ T_Q $

## Output Format

Output $ Q $ lines to the standard output. The $ i $-th line should contain the answer to query $ i $.

## Sample Input and Output

### Sample Input #1

```
5 6
3 5 2 1 5 3
2
1 3
2 5
```

### Sample Output #1

```
11
8
```

### Sample Input #2

```
10 10
3 1 4 1 2 9 3 2 7 10
10
1 7
1 4
3 8
6 9
3 4
1 8
7 10
4 10
3 5
6 9
```

### Sample Output #2

```
24
27
21
27
31
23
29
25
28
27
```

### Sample Input #3

```
100 20
6 97 94 50 96 51 94 86 92 77 9 73 21 9 46 42 76 77 49 17
20
38 87
20 60
5 56
8 82
69 80
13 42
90 99
97 98
96 97
95 97
61 88
48 61
11 73
42 81
8 18
78 83
17 54
41 68
2 69
72 100
```

### Sample Output #3

```
401
451
449
417
573
489
625
633
633
631
493
535
401
393
596
609
451
467
437
543
```

## Notes/Hints

### Constraints

- $ 2 \leq N, M \leq 300000 $
- $ 1 \leq Q \leq 300000 $
- $ 1 \leq A_i \leq N\ (1 \leq i \leq M) $
- $ A_i \neq A_{i+1}\ (1 \leq i \leq M-1) $
- $ 1 \leq S_i < T_i \leq N\ (1 \leq i \leq Q) $

### Subtasks

1. ($ 20 $ points) $ M, Q \leq 5000 $
2. ($ 50 $ points) $ N \leq 300, |A_i - A_{i+1}| \leq 10\ (1 \leq i \leq M-1) $
3. ($ 100 $ points) $ N \leq 300 $
4. ($ 280 $ points) $ N \leq 2000 $
5. ($ 300 $ points) $ M, Q \leq 50000 $
6. ($ 50 $ points) No additional constraints.

### Sample Explanation 1

In query $ 2 $, Penguin moves as follows:
1. Move from location $ 3 $ to location $ 2 $ ($ 1 $ second)
2. Use the warp to move from location $ 2 $ to location $ 5 $ ($ 1 $ second)
3. Use the warp to move from location $ 5 $ to location $ 2 $ ($ 1 $ second)
4. Move from location $ 2 $ to location $ 1 $ ($ 1 $ second)
5. Move from location $ 1 $ to location $ 2 $ ($ 1 $ second)
6. Use the warp to move from location $ 2 $ to location $ 5 $ ($ 1 $ second)
7. Move from location $ 5 $ to location $ 3 $ ($ 2 $ seconds)

Note that Penguin always moves in the shortest time possible. This input example satisfies the constraints of all subtasks.

### Sample Explanation 2

This input example satisfies the constraints of all subtasks.

### Sample Explanation 3

This input example satisfies the constraints of subtasks 1, 3, 4, 5, and 6. Original idea: \[define\](https://atcoder.jp/users/define)

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
