Vasiliy finally got to work, where there is a huge amount of tasks waiting for him. Vasiliy is given a matrix consisting of n rows and m columns and q tasks. Each task is to swap two submatrices of the given matrix. For each task Vasiliy knows six integers a i , b i , c i , d i , h i , w i , where a i is the index of the row where the top-left corner of the first rectangle is located, b i is the index of its column, c i is the index of the row of the top-left corner of the second rectangle, d i is the index of its column, h i is the height of the rectangle and w i is its width. It's guaranteed that two rectangles in one query do not overlap and do not touch, that is, no cell belongs to both rectangles, and no two cells belonging to different rectangles share a side . However, rectangles are allowed to share an angle. Vasiliy wants to know how the matrix will look like after all tasks are performed.

## Time Limit and Memory Limit

Time Limit: 2.5 seconds
Memory Limit: 256 megabytes

## Input Specification

The first line of the input contains three integers n , m and q ( 2 ≤  n ,  m  ≤ 1000 , 1 ≤  q  ≤ 10 000 ) — the number of rows and columns in matrix, and the number of tasks Vasiliy has to perform. Then follow n lines containing m integers v i ,  j ( 1 ≤  v i ,  j  ≤ 10 9 ) each — initial values of the cells of the matrix. Each of the following q lines contains six integers a i , b i , c i , d i , h i , w i ( 1 ≤  a i ,  c i ,  h i  ≤  n , 1 ≤  b i ,  d i ,  w i  ≤  m ).

## Output Specification

Print n lines containing m integers each — the resulting matrix.

## Examples

### Input #1
4 4 2
1 1 2 2
1 1 2 2
3 3 4 4
3 3 4 4
1 1 3 3 2 2
3 1 1 3 2 2

### Output #1
4 4 3 3
4 4 3 3
2 2 1 1
2 2 1 1

### Input #2
4 2 1
1 1
1 1
2 2
2 2
1 1 4 1 1 2

### Output #2
2 2
1 1
2 2
1 1

## Note

None

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
