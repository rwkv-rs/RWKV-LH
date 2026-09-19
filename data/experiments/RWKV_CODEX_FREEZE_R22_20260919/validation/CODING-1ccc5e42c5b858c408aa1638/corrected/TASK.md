Xiao A is a movie enthusiast who has collected hundreds of films and plans to select a few to watch during the holiday. Based on his taste and online reviews, he has assigned a score \( v_X \) to each movie \( X \), indicating his preference level. This score ranges from -1000 to 1000, with higher values indicating greater liking. Each time Xiao A watches a movie \( X \), his experience value increases by \( v_X \).

Additionally, since some movies are part of a series, such as the famous "Terminator" series and "The Matrix" series, Xiao A feels unsatisfied if he watches the prequel without watching the sequel. Specifically, for any two different movies \( X \) and \( Y \), there may be a dependency value \( d_{XY} \), indicating that if Xiao A watches \( X \) but not \( Y \), his experience value will decrease by \( d_{XY} \). (Note that this is independent of the viewing order; as long as both movies are watched, the experience value will not decrease.)

Now, he needs to select several movies to watch to maximize the total experience value. If he cannot achieve a positive experience value, the output should be 0.

## Input Format

The first line of input contains two integers: the total number of movies \( N \) and the number of dependency relationships \( M \). The second line contains \( N \) space-separated numbers, representing the scores for each movie. The next \( M \) lines each contain three integers \( X \), \( Y \), and \( d_{XY} \), indicating a dependency relationship. Each ordered pair \( (X, Y) \) appears at most once. \( (1 \leq X, Y \leq N) \)

## Output Format

Output a single integer, representing the maximum experience value Xiao A can obtain.

## Sample Input and Output

### Input Sample #1

```
2 2
100 -50
1 2 49
2 1 10
```

### Output Sample #1

```
51
```

## Notes

If Xiao A only watches movie 1, the experience value is \( 100 - 49 = 51 \). If he only watches movie 2, the experience value is \( -50 - 10 = -60 \). If he watches both movies, the experience value is \( 100 + (-50) = 50 \). Therefore, he should only watch movie 1.

### Data Size and Constraints

For 20% of the data, \( 1 \leq N \leq 15 \)

For 100% of the data, \( 1 \leq N \leq 100 \), \( -1000 \leq v_X \leq 1000 \), \( 0 < d_{XY} \leq 1000 \)

Each test case has a time limit of 1 second.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
