The general idea: You are given $n$ bend points in sequence that represent a pipeline. Note that these points are the upper coordinates of the pipeline, and the corresponding lower endpoint is $(x_i, y_i - 1)$. A beam of light is projected into the pipeline's entrance, and you need to determine the farthest horizontal coordinate that the light can reach. If the light can pass through the entire pipeline, output `Through all the pipe.`

## Input and Output Example

### Input Example #1

```
4
0 1
2 2
4 1
6 4
6
0 1
2 -0.6
5 -4.45
7 -5.57
12 -10.8
17 -16.55
0
```

### Output Example #1

```
4.67
Through all the pipe.
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
