There are two strings \(a\) and \(b\) each of length \(n\) consisting of lowercase letters. Extract all substrings of length \(k\) from each (there are \(n-k+1\) such substrings from each), which form sets \(A\) and \(B\) respectively. Now, modify the strings in set \(A\) such that \(A\) and \(B\) become identical. You can choose any string in \(A\) and modify a suffix of it any number of times, with the cost being the length of the suffix modified. The total cost is the sum of the costs of each modification. Find the minimum total cost.

## Input Format

The first line contains two integers \(n\) and \(k\) representing the length of the strings and the length of the substrings, respectively.  
The second line contains a string \(a\) of lowercase letters.  
The third line contains a string \(b\) of lowercase letters.

## Output Format

Output a single integer representing the minimum total cost.

## Sample Input and Output

### Input Sample #1

```
5 3
aabaa
ababa
```

### Output Sample #1

```
3
```

## Notes/Hints

### Sample Explanation

For sample 1, the substrings are: \(A = \{aab, aba, baa\}\) and \(B = \{aba, bab, aba\}\). It can be seen that one pair of \(aba\) is identical, and to make \(aab\) into \(aba\) (cost 2), and \(baa\) into \(bab\) (cost 1), the total cost is 3.

### Data Size and Constraints

For all data, \(1 \le k \le n \le 1.5 \times 10^5\).

- For 10% of the data, \(n \le 11\);
- For another 20% of the data, \(n \le 200\);
- For another 20% of the data, \(n \le 2000\);
- For another 10% of the data, each character of the string is uniformly random among lowercase letters;
- For the remaining 40% of the data, no special restrictions apply.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
