Yanagi is a high school student, and she is called "Hime" by her boyfriend who is a ninja fanboy. She likes picture books very much, so she often writes picture books by herself. She always asks you to make her picture book as an assistant. Today, you got asked to help her with making a comic.

She sometimes reads her picture books for children in kindergartens. Since Yanagi wants to let the children read, she wants to insert numbers to frames in order. Of course, such a task should be done by the assistant, you.

You want to do the task easily and fast, so you decide to write a program to output the order of reading frames based on the positions of the frames.

Write a program to print the number of order for each frame.

The comics in this problem satisfy the following rules.

The each comic is drawn on a sheet of rectangle paper. You can assume that the top side of the paper is on the x-axis. And you can assume that the right-hand side of the paper is on the y-axis. The positive direction of the x-axis is leftward. The positive direction of the y-axis is down direction. The paper is large enough to include all frames of the comic. In other words, no area in a frame is out of the paper.

The area of each frame is at least one. All sides of each frame are parallel to the x-axis or the y-axis. The frames can't overlap one another. However the frames may share the line of side.

You must decide the order to read  K , where  K  is a set of frames, with the following steps.


Step 1:You must choose an unread frame at the right-most position in K.
If you find such frames multiple, you must choose the frame at the top position among them.
If you can't find any unread frames, you stop reading K.
The frame you chose is "Starting Frame".
In step 1, you assume that the position of a frame is the top-right point of the frame.



Step 2:You should draw a line from the right-bottom point of "Starting Frame" to leftward horizontally.
If the line touch the right-hand side of other frame, you should stop drawing.
If the line is on the side of other frame, you should not stop drawing.
If the line touch the edge of paper, you should stop drawing.



Step 3:The set of the unread frames which are above the line ( they may be the bottom-side on the line ) drawn at Step 2 is L.
And you should read L.



Step 4: Go back to Step 1.


Constraints

0 < n < 10
(x0i != x1i) and (y0i != y1i)
0 ≤ x0i ,  y0i , x1i ,  y1i ≤ 500
Input

The input consists of multiple datasets. The last dataset is followed by a line containing one zero. You don't have to process this data.

Each datasets is in the following format.


n
x01 y01 x11 y11
x02 y02 x12 y12
....
x0n y0n x1n y1n



All numbers of the datasets are integer. They are separated by a space. The first line of a dataset contains one integer. n is the number of frames of the comic.  x0i ,  y0i ,  x1i ,  y1i are two non-neighboring points of  i  th frame in the line.

Output

Print n lines for each dataset. Print the number of order for ith frame in the ith line. And you should print blank line between the datasets.
Output format:


num1
num2
...
numi
...
numn


Example

Input

4
0 0 100 60
0 60 50 90
50 60 100 90
0 90 100 120
6
0 0 100 40
0 40 50 70
50 40 100 60
50 60 100 80
0 70 50 120
50 80 100 120
0


Output

1
2
3
4

1
2
4
5
3
6

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
