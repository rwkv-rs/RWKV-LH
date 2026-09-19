Given a piece of text, add commas according to specific rules.

The rules for adding commas are:

1. If a word is preceded by a comma, find all occurrences of that word in the text and add a comma before each of those occurrences, except if the occurrence is the first word of a sentence or already preceded by a comma.
2. If a word is succeeded by a comma, find all occurrences of that word in the text and add a comma after each of those occurrences, except if the occurrence is the last word of a sentence or already succeeded by a comma.
3. Repeat rules 1 and 2 until no new commas can be added.

The text length is between 2 and \(10^6\) characters.

The text has the following characteristics:

- The text starts with a word.
- Between every two words, there is either a single space, a comma followed by a space, or a period followed by a space (indicating the end of a sentence and the beginning of a new one).
- The last word of the text is followed by a period with no trailing space.

## Input Format

The input consists of one line of text, containing at least 2 characters and at most 1,000,000 characters. Each character is either a lowercase letter, a comma, a period, or a space. A word is defined as a maximal sequence of letters within the text. The text adheres to the following constraints:

- The text begins with a word.
- Between every two words in the text, there is either a single space, a comma followed by a space, or a period followed by a space (denoting the end of a sentence and the beginning of a new one).
- The last word of the text is followed by a period with no trailing space.

## Output Format

Display the result after applying Dr. Sprinkler's algorithm to the original text.

## Sample Input and Output

### Input Sample #1

```
please sit spot. sit spot, sit. spot here now here.
```

### Output Sample #1

```
please, sit spot. sit spot, sit. spot, here now, here.
```

### Input Sample #2

```
one, two. one tree. four tree. four four. five four. six five.
```

### Output Sample #2

```
one, two. one, tree. four, tree. four, four. five, four. six five.
```

## Notes

Time limit: 8 seconds, Memory limit: 1024 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
