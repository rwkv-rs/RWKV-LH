For ease of description, we assume all of Bob's friends are female.

Bob enjoys collecting stickers.

There are $n$ people and $m$ types of stickers in total.

Except for the first person (Bob), the other people will only exchange stickers they have duplicates of for stickers Bob does not have (they do not exchange with each other).

Bob is smarter than them and realizes that in certain situations, it might be more beneficial to exchange for a duplicate sticker.

The problem is to find out how many different types of stickers Bob can obtain at most.

## Input

$T$ test cases.

The first line for each test case contains $n, m$.

The following $n$ lines begin with a number $k_i$ representing the number of types of stickers the $i$-th person has, followed by $k_i$ numbers $a_j$ indicating the types of stickers the $i$-th person owns, one of each type.

**Note:** The first person in the input is Bob.

## Input and Output Example

### Input Example #1

```
2
2 5
6 1 1 1 1 1 1
3 1 2 2
3 5
4 1 2 1 1
3 2 2 2
5 1 3 4 4 3
```

### Output Example #1

```
Case #1: 1
Case #2: 3
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
