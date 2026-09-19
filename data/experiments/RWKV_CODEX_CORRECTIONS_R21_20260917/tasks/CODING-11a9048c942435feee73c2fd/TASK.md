A terrible flood arrived unexpectedly in the summer, and the Rabbit Kingdom faced an unprecedented famine. They had to venture into the forest outside to find food.

For simplicity, we assume there are \( n \) rabbits in the Rabbit Kingdom, numbered from 1 to \( n \). During the \( m \) days before relief food arrives, exactly \( k \) rabbits need to go into the forest to find food each day. The forest is inhabited by terrifying wolves, but fortunately, the rabbits have figured out the wolves' hunting habits, which is that the wolves will only hunt specific-numbered rabbits each day. For safety reasons, the rabbits need to ensure that the \( k \) rabbits going out to forage each day will not be hunted by the wolves.

Since the rabbits going out to forage each day are not the same, they define a "strangeness degree" \( p_i \) for each day, which is the number of rabbits that go out to find food on the \( i \)-th day but did not go out on the \( i-1 \)-th day. The strangeness degree for the first day is defined as 0.

Now, the rabbits hope to construct a legal plan under the premise of safety, ensuring that the strangeness degree for each day does not exceed \( l \).

## Input Format

The first line includes four integers \( n, m, k, l \).

Next, \( n \) lines follow, each containing a string of \( m \) '0's and '1's. The \( j \)-th character in the \( i \)-th line being '0' means that the wolf will hunt the rabbit numbered \( i \) on the \( j \)-th day, and '1' means it will not.

## Output Format

There will be \( m \) lines in total, each containing \( k \) distinct integers between 1 and \( n \), representing the numbers of the rabbits going out to find food on that day.

If there is no legal plan, output a single line `-1`.

## Sample Input and Output

### Input Sample #1

```
5 4 3 1
1001
1101
1111
1110
0111
```

### Output Sample #1

```
2 3 4
2 3 4
3 4 5
2 3 5
```

## Notes

### Sample 1 Explanation

For this sample, the sets of rabbits going out to forage over these 4 days are \(\{2, 3, 4\}; \{2, 3, 4\}; \{3, 4, 5\}; \{2, 3, 5\}\).

---

### Data Size and Constraints

- For 20% of the test cases, it is guaranteed that \( 1 \leq n, m \leq 10 \);
- For 100% of the test cases, it is guaranteed that \( 1 \leq n, m \leq 800 \), \( 1 \leq k \leq n \), \( 1 \leq l \leq k \).

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
