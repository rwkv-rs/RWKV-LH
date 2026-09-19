Farmer John has $N$ cows arranged in a line ($1 \leq N \leq 3 \cdot 10^5$). Unfortunately, a disease is spreading among them.

Initially, some cows are infected. Each night, the infected cows spread the disease to their adjacent cows (if they exist). Once a cow is infected, it remains infected.

After several nights, Farmer John realizes the situation is out of control, so he tests the cows to determine which ones are infected. Your task is to find the minimum number of cows that could have been initially infected.

## Input Format

The first line contains an integer $N$, the number of cows Farmer John has.

The next line contains a string of length $N$ consisting of $1$s and $0$s. A $1$ indicates an infected cow, and a $0$ indicates a cow that remains uninfected after several nights.

## Output Format

Output an integer representing the minimum number of cows that could have been initially infected.

## Sample Input and Output

### Sample Input #1

```
5
11111
```

### Sample Output #1

```
1
```

### Sample Input #2

```
6
011101
```

### Sample Output #2

```
4
```

## Notes/Hints

### Sample Explanation 1

Assuming only the middle cow was initially infected, the cows would be infected in the following sequence:

- Night $0$: $00100$ (the third cow is initially infected)
- Night $1$: $01110$ (the second and fourth cows are now infected)
- Night $2$: $11111$ (the first and fifth cows are now infected)
- Night $3$: $11111$ (all cows are already infected, no new infections)
- ...

After two or more nights, the cows' status matches the input. There are many other initial states and night counts that could have led to the input state, such as:

- Night $0$: $10001$
- Night $1$: $11011$
- Night $2$: $11111$

or:

- Night $0$: $01001$
- Night $1$: $11111$

or:

- Night $0$: $01000$
- Night $1$: $11100$
- Night $2$: $11110$
- Night $3$: $11111$

Among all these initial states, at least one cow is infected.

### Sample Explanation 2

The only initial state and night count that could lead to this final state is: without any nights, the four infected cows in the input were all initially infected.

### Test Point Properties

- Test points $3-7$ satisfy $N \leq 1000$.
- Test points $8-12$ have no additional restrictions.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
