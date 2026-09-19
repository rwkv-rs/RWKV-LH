Dolan has a stack of card. Each card is numbered from 1 to n from top to bottom. His nephews want to play with the cards. Each nephew can only do one kind of operation.

Nephew number 1 will reverse the order of the card from i-th to j-th position.

Nephew number 2 will ask uncle Dolan what is the card number on i-th position.

Nephew number 3 will ask uncle Dolan in what position is the card number i.

Since Dolan is a good uncle, he will have to answer all questions correctly. Please help Dolan.

## Input Format

First line on input is n and q, the number of cards (n < 100000) and number of operations by the nephews (q < 100000). The next q lines will contain the operation by the nephews.

For each operation, the first number will be the nephew number. The second (and possibly third) number is i (and j) from the description above (1 < i < j < n).

## Output Format

For each question asked by the nephews (operation 2 and 3), output a single line containing the answer.

## Sample Input and Output

### Sample Input #1

```
10 5\n1 2 6\n2 5\n1 4 9\n3 4\n2 4&nbsp;
```

### Sample Output #1

```
3\n9\n9&nbsp;
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
