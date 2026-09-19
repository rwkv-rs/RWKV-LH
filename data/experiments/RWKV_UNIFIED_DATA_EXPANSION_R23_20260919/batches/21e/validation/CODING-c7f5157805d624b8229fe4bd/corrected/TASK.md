Farmer John's cows have a sweet tooth, especially for candy canes. FJ has $N$ cows, each with a specific initial height. He plans to feed them $M$ candy canes, each with a unique height ($1 \le N, M \le 2 \cdot 10^5$).

FJ will feed the cows the candy canes in the order given in the input. The cows will then line up in the order given and approach the candy cane one by one. Each cow can only eat up to its height (since they can't reach higher). Even if a cow eats the bottom of the candy cane, the candy cane remains in its original hanging position and is not lowered to the ground. If the bottom of the candy cane is already higher than a cow's height, that cow might eat nothing during its turn. After each cow has had a turn, their height increases by the amount of candy cane they ate, and Farmer John hangs the next candy cane, repeating the process (with the first cow starting again).

## Input Format

The first line contains $N$ and $M$.

The next line contains the initial heights of the $N$ cows, each within the range $[1, 10^9]$.

The next line contains the lengths of the $M$ candy canes, each within the range $[1, 10^9]$.

## Output Format

Output $N$ lines, representing the final heights of each cow.

Note that due to the large size of the integers involved, you may need to use a 64-bit integer data type (e.g., `long long` in C/C++).

## Sample Input and Output

### Input Sample #1

```
3 2
3 2 5
6 1
```

### Output Sample #1

```
7
2
7
```

## Notes

### Sample Explanation 1

The first candy cane is 6 units high.

- The first cow eats the first candy cane up to height 3, leaving the remaining part [3, 6].
- The second cow is not tall enough to eat any remaining part of the first candy cane.
- The third cow eats an additional two units of the first candy cane. The remaining part [5, 6] of the first candy cane is not eaten.

Next, each cow grows according to the amount they ate, so the cow heights become [3+3, 2+0, 5+2] = [6, 2, 7].

The second candy cane is 1 unit high and is completely eaten by the first cow.

### Test Case Properties

- Test cases $2-10$ satisfy $N, M \le 10^3$.
- Test cases $11-14$ have no additional restrictions.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
