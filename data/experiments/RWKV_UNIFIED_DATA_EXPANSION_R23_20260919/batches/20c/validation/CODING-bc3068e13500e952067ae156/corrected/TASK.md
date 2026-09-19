The English teacher has assigned $N$ reading comprehension tasks, but each English passage contains many unfamiliar words that need to be looked up in a dictionary. To save time, a statistical analysis needs to be done to determine in which articles certain unfamiliar words have appeared.

## Input Format

The first line is an integer $N$, indicating the number of articles, where each article contains only spaces and lowercase letters.

The next $N$ lines describe each article. The beginning of each line is an integer $L$, indicating that the article consists of $L$ words. Following this are $L$ words separated by a space.

Next is an integer $M$, indicating how many queries need to be made. The following $M$ lines each represent a word to be queried.

## Output Format

For each queried word, output a line listing the article numbers in which it has appeared, sorted in ascending order without duplicates. Article numbers should be separated by a space (note that there should be no space before the first number or after the last number). If the word has never appeared, output an empty line.

## Sample Input and Output

### Input Sample #1

```
3
9 you are a good boy ha ha o yeah
13 o my god you like bleach naruto one piece and so do i
11 but i do not think you will get all the points
5
you
i
o
all
naruto
```

### Output Sample #1

```
1 2 3
2 3
1 2
3
2
```

## Notes

For $30\%$ of the data, $1 \le M \le 10^3$.

For $100\%$ of the data, $1 \le M \le 10^4$, $1 \le N \le 10^3$.

The length of each article (including spaces between words) $\le 5 \times 10^3$ characters, and the length of each word $\le 20$ characters.

Each test case has a time limit of 2 seconds.

Thanks to @Zhong Zijun for adding a set of data.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
