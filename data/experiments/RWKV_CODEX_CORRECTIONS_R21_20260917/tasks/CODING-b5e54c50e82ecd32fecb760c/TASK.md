Old MacDonald has a farm, where he has a cow and a circular pasture fenced in, with a radius of 100 yards. He plans to tie the cow to a post located on the perimeter of the pasture and wants the cow to be able to graze on exactly one-third of the pasture's grass. How long should the rope be to achieve this?

You need to solve a more challenging version of this problem.

## Input Format

The first line is an integer, indicating the number of datasets. Each dataset is formatted as described below.

There is a blank line following the first line, and there are also blank lines between two consecutive datasets. For each dataset, two numbers are input: the radius \( R \) (1 ≤ \( R \) ≤ 1000) and the area \( P \) that he wants the cow to graze.

## Output Format

For each dataset, solve Old MacDonald's problem: What length of rope should Old MacDonald use so that the cow can graze on an area of \( P \) within a circular pasture of radius \( R \)? Round the answer to two decimal places. Output a statement for each dataset in the format shown in the sample output. Numbers \( P \) in the input and the answer in the output should be rounded to two decimal places. The outputs for two consecutive datasets should be separated by a blank line.

## Sample Input

```
100 0.33
```

## Sample Output

```
r=100, P=0.33, Rope=13.24
```

## Hints and Notes

Note: The recommended value for \( \pi \) is \( 2 \times \text{acos}(0) \), but any value for \( \pi \) that is within a difference of no more than \( 1e-10 \) from the exact value will be judged as correct. The sample output value 13.24 is incorrect and is only used to show you the correct format.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
