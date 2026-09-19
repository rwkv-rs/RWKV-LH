The secret services of Armin, an otherwise peace-loving country, have decided to perform a surgical strike in the war-torn city of Tashka. Tashka is under enemy control and the objective of the strike is to gain control over the city. 
The mission is subdivided into the following steps:
1) Divide in groups and infiltrate all enemy bases in Tashka as unarmed civilians, and find the status of enemy's defense strength at that base.
 ( You can assume that the number of groups are sufficiently large to cover each base separately )
2) Pick up the required amount of ammunition from our secret ammunition store in the city.
3) Return to the bases and destroy the enemy defense.
4) Rush to the Town Hall for the Helicopter pick up out of the town.  

There are a total of  N buildings in Tashka, numbered from 1 to N .  The agents will be dropped at building denoted by S, post which they will divide into groups and each enemy base will have a group moving towards it. The ammunition store is denoted by A and town hall is denoted by H . All the buildings except these three are enemy bases and are to be infiltrated.  There are a total of M bidirectional roads in the city, each road connects two cities. There can be multiple roads between a pair of cities and each road has a time taken to cross associated with its terrain.
Monk is made in charge of the pickup.  He can not land the Helicopter before all the groups have arrived at the Town Hall. Find the Minimum units of Time,  post dropping the agents, that the Helicopter should be landed such that all groups are able to reach the Town Hall.
Input:
First line contains an integer T. T test cases follow.
First line of each test cases contains two space-separated integers N, M.
Each of the next M lines contains three space-separated integers X, Y, C, denoting that there is a bidirectional road between X and Y that needs C units of time to cross. 
The next line contains three space-separated integers S, A and H (not necessarily distinct) .  

Output:
Print the answer to each test case in a new line.  

Constraints:
1 ≤ T ≤ 10
4 ≤ N ≤ 100
1 ≤ M ≤ 10000
1 ≤ X, Y, S, A, H  ≤ N
1 ≤ C ≤ 100  

Note:
Time taken to note status of enemy defense, load ammunition or attack enemy enemy base can be considered negligible compared to time taken to travel.

SAMPLE INPUT
1
4 4
1 4 1
1 2 1
2 3 1
2 4 1
1 2 3

SAMPLE OUTPUT
5

Explanation

Agents start at 1, rush to enemy base at 4 (Time taken =2 units). Go to ammunition store at 2, and return back to attack enemy base (Time taken=2 units) , destroy the base and head off to pickup point (Time taken =1 units).
Hence, 2+2+1= 5units.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
