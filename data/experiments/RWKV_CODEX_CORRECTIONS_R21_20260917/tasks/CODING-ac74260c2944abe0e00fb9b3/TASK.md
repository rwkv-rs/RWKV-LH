This year too, the time has come for the National Programming Championships. In the district tournament where the right to participate in the national tournament is bet, 2n teams will face each other in a one-on-one winning tournament system.

Team numbers 0, .. .2n − 1 are assigned to the tournament table, and the confrontation procedure from the first round to the nth round is as follows.

1. In the first round, (team with team number l) and (team with team number l + 1) will face each other. (l ≡ 0 (mod 2))
2. In the i + 1st round (1 ≤ i <n), "the team whose team number is l or more and less than l + 2i who has not lost even once in the confrontation up to the i round" and "the team number is l" Of the teams with + 2i or more and less than l + 2i + 1, the team that has never lost in the confrontation up to the i round will confront. (l ≡ 0 (mod 2i + 1))


After the nth round, the ranking of each team is fixed at 2n − (the number of times that team has won). Since there is no draw in this confrontation, one of the confronting teams wins and the other loses.

As we were selected to represent the district conference on a sunny day, we decided to have the manager examine the results of other district conferences. The result of the examination here was the "ranking table received from the manager". To explain the "ranking table received from the manager" in more detail, the ranking of the team with team number i is written in the i (0 ≤ i ≤ 2n − 1) th element in a sequence of length 2n. ..

However, the "stands received from the manager" had a large number of the same rankings! Due to the rules of the tournament, it is unlikely that the same ranking will be lined up in large numbers. Therefore, let's calculate the minimum number of teams to change the ranking in order to make the "standings received from the manager" a "consistent standings" and tell the manager how wrong the standings are. A "consistent standings" is a standings that can occur as a result of a tournament with a fixed ranking.
Input

The "ranking table received from the manager" is given to the input in the following format.


n m
a0 a1 .. .am
b0 b1 ... bm−1


* The first line consists of two integers, n and m, where 2n is the "number of participating teams in the district tournament" and m is the "number of sections in which consecutive rankings are lined up in the" standings received from the manager "". Represents.
* The second line consists of m + 1 integers of ai (0 ≤ i ≤ m), and each ai represents "the division position of the section where consecutive rankings are lined up in the'ranking table received from the manager'". ..
* The third line consists of m integers of bi (0 ≤ i <m), and each 2bi represents "the ranking of teams whose team numbers are greater than or equal to ai and less than ai + 1 in the standings received from the manager". ..



Constraints

* 1 ≤ n ≤ 30
* 1 ≤ m ≤ 10,000
* 0 = a0 <a1 ≤ ... ≤ am−1 <am = 2n
* 0 ≤ bi ≤ n



Output

Output the minimum number of teams to change the ranking in one line so that the "standings received from the manager" becomes a "consistent standings".

Sample Input 1


1 1
0 2
1


Output for the Sample Input 1


1


There are two "consistent standings" with 2 participating teams: {"ranking of teams with team number 0" and "ranking of teams with team number 1"}, {1, 2} and {2, 1}. There is. In order to modify the standings {2, 2} to a "consistent standings", the ranking of one of the teams must be changed to 1.

Sample Input 2


twenty three
0 1 2 4
0 1 2


Output for the Sample Input 2


2


Sample Input 3


twenty three
0 1 3 4
0 2 1


Output for the Sample Input 3


0


Sample Input 4


4 5
0 1 2 4 8 16
0 1 2 3 4


Output for the Sample Input 4


Ten






Example

Input

1 1
0 2
1


Output

1

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
