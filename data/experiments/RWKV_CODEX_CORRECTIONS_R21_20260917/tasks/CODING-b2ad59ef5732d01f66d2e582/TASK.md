### Problem Statement

In a certain continent, there is a tribe called `Eeny Meeny`. The origin of this tribe's name is related to the way they elect their tribal chief each year. It is said that a journalist visited the tribe and attempted to introduce some aspects of modern civilization to them; however, a misfortunate end prevented him from ever completing his work. Thus, the tribe no longer has a permanent chief; the term of the chief lasts only one year. At the end of their term, the chief will be eaten by the people, and a new chief will be selected. Their method of selection is called `Eeny meeny miny mo`. Specifically, all eligible tribal members stand in a circle, with a starting position decided. The chief shaman counts around the circle, starting with the first person, with the sequence: $E~e~n~y~m~e~e~n~y~m~i~n~y~m~o$. If there are people left unnumbered after completing this sequence, the counting is repeated. Each time, the person at the position marked as `o` is removed from the circle, and the circle closes, with counting starting again from the neighbor (the next person to be marked `E`). This process is repeated until only one person remains, who is then selected as the chief.

Despite the strong allure of the chief's position for a one-year term, this brief glory does not interest you. You have figured out that this year's counting will start from `Mxgobgwq` and now want to know which position should not be occupied. You are unsure of the counting direction and the number of candidates, but you can estimate the range of the number of candidates (which is definitely a number less than or equal to $10^6$).

### Input Format

The input consists of several lines, with each line containing the upper and lower bounds (inclusive) of the estimated number of candidates. The input ends when a line containing two `0`s is encountered.

### Output Format

The output consists of several lines, each corresponding to a line of input. Each line contains a number indicating a position that, for every candidate number within the estimated range, will never be selected as chief regardless of counting direction, and is closest to `Mxgobgwq`. If no such safe position exists, output `Better estimate needed`.

## Input and Output Example

### Input Example #1

```
80 150
40 150
0 0
```

### Output Example #1

```
1
Better estimate needed
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
