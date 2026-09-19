There are n hens in a farm. The egg hatching ability of all the hens decreases by 1 day after each time they hatch an egg. (i.e. every hen will hatch the next egg 1 day slower than the time it took to hatch the previous egg)

Let the initial egg hatching ability of Hen\[i\] be D\[i\].

- Hen\[i\] lays it's first egg on D\[i\]th day.
- Hen\[i\] lays it's second egg on 2\*D\[i\]+1 th day.
- Hen\[i\] lays it's thrid egg on 3\*D\[i\]+3rd day.
- Hen\[i\] lays it's fourth egg on 4\*D\[i\]+6th day.
- Hen\[i\] lays it's fifth egg on 5\*D\[i\]+10th day.

and so on..

Given **n** - the number of hens and the array **D** - the initial egg hatching ability of the hens, find the minimum number of days required to produce at least **K** eggs. You can safely assume that eggs neither gets damaged nor converted into hens.

## Input Format

The first line consists of integers **t**, the number of test cases. For each test case, the first line consists two integers **n** and **K**. The next line consists of **n** integers representing the initial egg hatching ability of the hens.

## Output Format

For each test case, find the minimum number of days required to produce at least **K** eggs.

## Sample Input and Output

### Sample Input #1

```
3
1 4
1
2 5
2 5
5 1000000
1 2 3 4 5
```

### Sample Output #1

```
10
11
20000500003
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
