Farmer John is trying to sort his $N$ cows (numbered $1 \ldots N$, where $1 \le N \le 100$) before they head to the pasture for breakfast.

Currently, the cows are arranged in the order $p_1, p_2, p_3, \ldots, p_N$, with Farmer John standing in front of cow $p_1$. He wants to rearrange the cows so that their order becomes $1, 2, 3, \ldots, N$, with cow $1$ next to Farmer John.

The cows are sleepy today, so only the cow directly facing Farmer John will pay attention to his instructions. Each time, he can command this cow to move back by $k$ steps, where $k$ can be any number in the range $1 \ldots N-1$. The $k$ cows she passes will move forward to make space for her to insert into the position behind these cows.

For example, suppose $N=4$ and the cows start in the following order:

> FJ: $4, 3, 2, 1$

The only cow paying attention to FJ's instructions is cow $4$. When he commands her to move back by $2$ steps, the order becomes:

> FJ: $3, 2, 4, 1$

Now, the only cow paying attention to FJ's instructions is cow $3$, so he can command cow $3$ next, and so on until the cows are sorted.

Farmer John is eager to finish sorting so he can return to his farmhouse for his own breakfast. Help him determine the minimum number of operations required to sort the cows.

## Input Format

The first line of input contains $N$.

The second line contains $N$ space-separated integers, $p_1, p_2, p_3, \ldots, p_N$, representing the initial order of the cows.

## Output Format

Output a single integer, the minimum number of operations required for Farmer John to sort the $N$ cows using the best strategy.

## Sample Input and Output

### Sample Input #1

```
4
1 2 4 3
```

### Sample Output #1

```
3
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
