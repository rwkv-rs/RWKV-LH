### Problem Statement:
A music player has a so-called shuffle play function. Suppose there are a total of `s` songs; initially, these songs are randomly shuffled. Once all songs have been played, they are shuffled again, and the playback continues. Note: Before all `s` songs are played, they will not be shuffled again, so every sequence of `s` songs in the playback record is a permutation of numbers from 1 to `s`.

### Input:
You are given a playback record of length `n` (1 <= `s`, `n` <= 100,000) denoted by `xi` (1 <= `xi` <= `s`).

### Output:
Count the number of possible times the next shuffle can occur.

## Input and Output Samples

### Input Sample #1

```
4
4 10
3 4 4 1 3 2 1 2 3 4
6 6
6 5 4 3 2 1
3 5
3 3 1 1 1
7 3
5 7 3
```

### Output Sample #1

```
1
6
0
7
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
