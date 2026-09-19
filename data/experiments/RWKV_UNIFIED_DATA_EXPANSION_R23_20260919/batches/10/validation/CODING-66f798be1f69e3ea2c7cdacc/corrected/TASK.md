It's noon, and Doraemon is ready to eat his cat food.

Doraemon takes out \( n \) portions of food, where the \( i \)-th portion contains \( w[i] \) units of energy. Doraemon can choose to eat some of these portions to gain the total energy from them.

Doraemon doesn't want to become too fat or too thin, so he has specified a target interval \([l, r]\). Clearly, there may be many ways to choose the food to achieve this target, and Doraemon wants to know the total number of such schemes.

## Input Format

The first line contains three positive integers \( n, l, r \).

The second line contains \( n \) positive integers representing the energy \( w[i] \) of each portion of food.

## Output Format

A single line containing one integer, representing the number of schemes.

## Sample Input and Output

### Input Sample #1

```
4 70 85
10 10 20 50
```

### Output Sample #1

```
4
```

## Notes

### Sample Explanation

All possible schemes are:

- Choose food 1, 2, 4, energy 10 + 10 + 50 = 70
- Choose food 1, 3, 4, energy 10 + 20 + 50 = 80
- Choose food 2, 3, 4, energy 10 + 20 + 50 = 80
- Choose food 3, 4, energy 20 + 50 = 70

There are 4 schemes in total.

### Data Size and Constraints

For 50% of the data, \( n \leq 20 \).

For 100% of the data, \( n \leq 40 \), \( 20 \leq w[i] \leq 100 \), \( l \leq r \leq 300 \).

Hint: \( w[i] \) is uniformly randomly generated within the given range.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
