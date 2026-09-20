Natsume loves big cats. One day, Natsume was invited by the stray cats she was always close to to go to the mysterious bookstore where the cats were open. When I heard that the bookstore sells books with many pictures of cats, Natsume decided to follow her happily.

I didn't know Natsume, but the bookstore that was taken by the cats was a famous store with chain stores nationwide. The store has a solid manual for the clerk, and the behavior of the clerk is unified in every store. The following is an excerpt from the manual.

1. When a customer enters the store through a door within a 10-Euclidean distance from the clerk, he must say "Welcome Hello" in a loud voice for X seconds.
2. When the clerk who heard another clerk within the Euclidean distance of 50 saying "Welcome Hello", the clerk said "Welcome Hello" at the end of the utterance of "Welcome Hello" in a loud voice over X seconds. Must. However, a clerk who has completed uttering another "Welcome Hello" within the past Y seconds from the start of uttering this repeat must not repeat it.



Given the X, Y, customer location, and clerk placement, calculate how many seconds it will take for the store to be quiet after the customer enters. If the repeat does not stop, print "You're always welcome!".

Notes on Submission

Multiple datasets are given in the above format. The first line of
input data gives the number of datasets. Create a program that outputs the output for each data set in order in the above format.



Input

The number N of the clerk and the X and Y written in the manual are given on the first line of the input, separated by one space character. The second line is the position where Natsume enters the store, and the following N lines are the coordinates representing the positions of N clerk. Each position is given by separating the x and y coordinates with a single space character, and each number is given as an integer between 0 and 1000. Also, 1 <= N <= 1000, 1 <= X, Y <= 100 is satisfied.

Output

If the repeat does not stop, output the time from when the customer enters the store until it becomes quiet, and if it does not stop, output "You're always welcome!" On one line.

Example

Input

4
3 3 5
0 0
10 0
40 40
40 90
4 5 10
100 100
50 100
50 150
100 50
100 150
4 60 10
100 100
90 100
110 100
100 90
100 110
4 60 10
100 100
80 100
110 100
100 80
100 110


Output

9
0
60
You're always welcome!

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
