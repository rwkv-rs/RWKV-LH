Competitive programming is very popular in Byteland. In fact, every Bytelandian citizen is registered at two programming sites -- CodeCoder and TopForces. Each site maintains its own proprietary rating system. Each citizen has a unique integer rating at each site that approximates their skill. Greater rating corresponds to better skill.

People of Byteland are naturally optimistic. Citizen A thinks that he has a chance to beat citizen B in a programming competition if there exists a sequence of Bytelandian citizens \( A = P_{0}, P_{1},...,P_{k} = B \) for some \( k \ge 1 \) such that for each \( i (0 \le i < k) \), \( P_{i} \) has higher rating than \( P_{i+1} \) at one or both sites.

Each Bytelandian citizen wants to know how many other citizens they can possibly beat in a programming competition.

## Input Format

The first line of the input contains an integer \( n \) -- the number of citizens \( (1 \le n \le 100,000) \). The following \( n \) lines contain information about ratings. The \( i \)-th of them contains two integers \( CC_{i} \) and \( TF_{i} \) -- ratings of the \( i \)-th citizen at CodeCoder and TopForces \( (1 \le CC_{i}, TF_{i} \le 10^{6}) \). All the ratings at each site are distinct.

## Output Format

For each citizen \( i \), output an integer \( b_{i} \) -- how many other citizens they can possibly beat in a programming competition. Each \( b_{i} \) should be printed in a separate line, in the order the citizens are given in the input.

## Sample Input and Output

### Input Sample #1

```
4
2 3
3 2
1 1
4 5
```

### Output Sample #1

```
2
2
0
3
```

## Notes/Hints

Time limit: 2 seconds, Memory limit: 256 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
