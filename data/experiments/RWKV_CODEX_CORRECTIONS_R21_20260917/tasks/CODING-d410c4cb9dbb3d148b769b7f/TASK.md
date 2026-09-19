Chef Serge of the renowned restaurant *Salt, Pepper & Garlic* is ready to become a Michelin-starred chef. He has been informed that a secret reviewer will be visiting his restaurant tonight.

Although he does not know the reviewer's name, he has been given the reviewer's preferred dish and taste preferences. Specifically, the reviewer wants the dish to include a very precise ratio of salt, pepper, and garlic powder.

Serge has several bottles of mixed spices on a shelf in his kitchen. For each bottle, he knows the quantities of salt, pepper, and garlic powder (in kilograms) mixed in it. He can mix any number of these bottles (or use a single bottle) to achieve the required ratio of spices.

The amount of spices used in the dish is negligible, so it can be assumed that the spices are sufficient. However, the ratios of salt, pepper, and garlic powder required by the reviewer can be very large.

Serge wants to determine if he can use the existing bottles to prepare the spices in the required ratio. If possible, he wants to know the minimum number of bottles needed.

Additionally, Serge may receive new bottles or give away existing ones, meaning the types of bottles on the shelf will constantly change. Serge wants to solve the above problem each time the shelf's contents change.

For example, if the reviewer requires a ratio of $1:1:1$ for salt, pepper, and garlic powder, and the shelf has the following bottles:

| Bottle Number | Salt | Pepper | Garlic Powder |
| :-----------: | :--: | :----: | :-----------: |
|       1       |  10  |   20   |      30       |
|       2       | 300  |  200   |      100      |
|       3       |  12  |   15   |      27       |

Then, mixing all of bottle 1 and 60 kilograms of bottle 2 (including 30 kg of salt, 20 kg of pepper, and 10 kg of garlic powder) will meet the requirement. Once bottle 2 is removed, it is impossible to meet the reviewer's requirement.

## Input Format

The first line contains three integers $S_f, P_f, G_f$, representing the ratio of salt, pepper, and garlic powder required by the reviewer. For any $\alpha > 0$, $(\alpha S_f, \alpha P_f, \alpha G_f)$ also meets the reviewer's requirement.

The next line contains an integer $N$, representing the number of changes to the bottles on the shelf. Initially, there are no bottles on the shelf.

The following $N$ lines describe each change:

- If a new bottle is added, the line contains a capital letter `A` and three integers $S_i, P_i, G_i$, representing the quantities of salt, pepper, and garlic powder in the bottle. Bottles are numbered sequentially starting from 1 based on the order they are added.
- If a bottle is removed, the line contains a capital letter `R` and an integer $r_i$, representing the number of the removed bottle. It is guaranteed that the bottle with this number is on the shelf.

## Output Format

Output $N$ lines. The $i$-th line should output the minimum number of bottles needed to meet the reviewer's requirement after the $i$-th change. If no solution exists, output $0$.

## Sample Input and Output

### Input Sample #1

```
1 2 3
6
A 5 6 7
A 3 10 17
R 1
A 15 18 21
A 5 10 15
R 3
```

### Output Sample #1

```
0
2
0
2
1
1
```

## Notes/Hints

All data satisfies: $1 \leq N \leq 10^5$, $S_f, P_f, G_f \geq 0$, $0 < S_f + P_f + G_f \leq 10^6$, $S_i, P_i, G_i \geq 0$, $0 < S_i + P_i + G_i \leq 10^6$.

- Subtask 1 (13 points): $N \leq 50$, $0 < S_i + P_i + G_i \leq 10^2$;
- Subtask 2 (17 points): $N \leq 500$, $0 < S_i + P_i + G_i \leq 10^3$;
- Subtask 3 (30 points): $N \leq 5000$, $0 < S_i + P_i + G_i \leq 10^4$;
- Subtask 4 (40 points): No additional constraints.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
