Alice received a set of Toy Train™ from Bob. It consists of one train and a connected railway network of n stations, enumerated from 1 through n. The train occupies one station at a time and travels around the network of stations in a circular manner. More precisely, the immediate station that the train will visit after station i is station i+1 if 1 ≤ i < n or station 1 if i = n. It takes the train 1 second to travel to its next station as described.

Bob gave Alice a fun task before he left: to deliver m candies that are initially at some stations to their independent destinations using the train. The candies are enumerated from 1 through m. Candy i (1 ≤ i ≤ m), now at station a_i, should be delivered to station b_i (a_i ≠ b_i).

<image> The blue numbers on the candies correspond to b_i values. The image corresponds to the 1-st example.

The train has infinite capacity, and it is possible to load off any number of candies at a station. However, only at most one candy can be loaded from a station onto the train before it leaves the station. You can choose any candy at this station. The time it takes to move the candies is negligible.

Now, Alice wonders how much time is needed for the train to deliver all candies. Your task is to find, for each station, the minimum time the train would need to deliver all the candies were it to start from there.
Input

The first line contains two space-separated integers n and m (2 ≤ n ≤ 100; 1 ≤ m ≤ 200) — the number of stations and the number of candies, respectively.

The i-th of the following m lines contains two space-separated integers a_i and b_i (1 ≤ a_i, b_i ≤ n; a_i ≠ b_i) — the station that initially contains candy i and the destination station of the candy, respectively.

Output

In the first and only line, print n space-separated integers, the i-th of which is the minimum time, in seconds, the train would need to deliver all the candies were it to start from station i.

Examples

Input


5 7
2 4
5 1
2 3
3 4
4 1
5 3
3 5


Output


10 9 10 10 9 


Input


2 3
1 2
1 2
1 2


Output


5 6 

Note

Consider the second sample.

If the train started at station 1, the optimal strategy is as follows.

  1. Load the first candy onto the train. 
  2. Proceed to station 2. This step takes 1 second. 
  3. Deliver the first candy. 
  4. Proceed to station 1. This step takes 1 second. 
  5. Load the second candy onto the train. 
  6. Proceed to station 2. This step takes 1 second. 
  7. Deliver the second candy. 
  8. Proceed to station 1. This step takes 1 second. 
  9. Load the third candy onto the train. 
  10. Proceed to station 2. This step takes 1 second. 
  11. Deliver the third candy. 



Hence, the train needs 5 seconds to complete the tasks.

If the train were to start at station 2, however, it would need to move to station 1 before it could load the first candy, which would take one additional second. Thus, the answer in this scenario is 5+1 = 6 seconds.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
