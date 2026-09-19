Just like humans, cows often appreciate feeling they are unique in some way. Since Farmer John's cows all come from the same breed and look quite similar, they want to measure uniqueness in their names.

Each cow's name has some number of substrings. For example, "amy" has substrings {a, m, y, am, my, amy}, and "tommy" would have the following substrings: {t, o, m, y, to, om, mm, my, tom, omm, mmy, tomm, ommy, tommy}.

A cow name has a "uniqueness factor" which is the number of substrings of that name not shared with any other cow. For example, if "amy" was in a herd by herself, her uniqueness factor would be 6. If "tommy" was in a herd by himself, his uniqueness factor would be 14. If they were in a herd together, however, "amy's" uniqueness factor would be 3 and "tommy's" would be 11.

Given a herd of cows, please determine each cow's uniqueness factor.

Define a string's "uniqueness value" as the number of distinct non-empty substrings that belong exclusively to that string. For instance, for the strings "amy" and "tommy", the substrings unique to "amy" are "a", "am", and "amy", totaling 3. The substrings unique to "tommy" are "t", "to", "tom", "tomm", "tommy", "o", "om", "omm", "ommy", "mm", and "mmy", totaling 11. Therefore, "amy" has a uniqueness value of 3, and "tommy" has a uniqueness value of 11.

Given \( N \) (\( N \leq 10^5 \)) strings with characters from a-z, where the total length of all strings is less than \( 10^5 \), calculate the uniqueness value for each string.

## Input Format

The first line of input contains \( N \) (\( 1 \le N \le 10^5 \)). The following \( N \) lines each contain the name of a cow in the herd. Each name consists of lowercase letters a-z. The total length of all names does not exceed \( 10^5 \).

## Output Format

Output \( N \) numbers, one per line, representing the uniqueness factor of each cow.

## Sample Input and Output

### Sample Input #1

```
3
amy
tommy
bessie
```

### Sample Output #1

```
3
11
19
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
