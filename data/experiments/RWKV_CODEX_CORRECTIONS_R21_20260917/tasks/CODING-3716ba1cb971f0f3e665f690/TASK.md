In a popular online game on JLOI, contestants are required to answer very difficult questions. If a contestant cannot answer within the specified time, the system will provide 1 hint, followed by the 2nd and 3rd hints sequentially. The characters that appear in the answer include letters and the following symbols:

`. , : ; ! ? -` and spaces (spaces will not appear at the beginning or end).

Letters refer to: lowercase letters `a` to `z` and uppercase letters `A` to `Z`, where `a e i o u A E I O U` are vowels.

The rules for generating hints are as follows:

- The 1st hint: Simply replace all letters with `.`.
- The 2nd hint: Derived from the 1st hint, count the number of letters, divide the total by three, and take the nearest natural number \( N \), then display the first \( N \) letters from the 1st hint.
- The 3rd hint: Derived from the 2nd hint, display the remaining vowels. If there are no vowels to display, then derive from the 1st hint, i.e., display the first \( \frac{2}{3} \) of the letters (take the nearest integer if not divisible by 3).

## Input Format

A single line containing the question, with a maximum of 50 characters.

## Output Format

Three lines: The three hints output according to the rules.

## Sample Input and Output

### Sample Input #1

```
Upomoc! Lpv s nm pkrl sv smglsnk.
```

### Sample Output #1

```
......! ... . .. .... .. ........ 
Upomoc! Lp. . .. .... .. ........ 
Upomoc! Lpv s nm pkrl s. ........
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
