You are travelling to Kullu Manili, a hill station in India. You saw some huge mountains and very curious to climb the highest ones. Assume that there are **n** mountains of height **hi** given.

But you were wondering about what could be the total height i need to climb if I climb only the mountain of maximum height only in a segment of k continuous mountains, considering all k segements possible. You want to calculate this for all k, such that 1<=k<=n.

Mathematically, we need to find the sum of maximum element in each possible continuous segment of size k.

## Input Format

The first line contains an input **n**.

Then **n** numbers follow, denoting the height of **ith** mountain.

## Output Format

Output **n** lines, where ith line contains the sum of height of mountains to climb considering all continuous segments of size **i**.

## Sample Input and Output

### Sample Input #1

```
5
5 3 4 2 3
```

### Sample Output #1

```
17
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
