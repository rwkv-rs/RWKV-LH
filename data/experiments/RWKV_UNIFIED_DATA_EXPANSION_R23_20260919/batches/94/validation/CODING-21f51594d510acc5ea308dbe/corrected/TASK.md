In ancient southern China, there was a princess whom the king adored. One day, she went missing, and the king sent knights to find her. Eventually, they discovered that the princess had been kidnapped by the demon Diablo. All the knights were terrified, and the king was very angry and worried. In this dire moment, a young man showed his courage, risking his life to rescue the princess alone. However, the demon's lair was very dangerous, dark, and cold. If he went unprepared, he would die. The dungeon was built inside a large pit underground. In front of the dungeon was a large underground hall, so sunlight couldn't reach the demon. Hence, the young man couldn't enter the dungeon directly. After pondering, he finally came up with a solution. The hall had two openings, an entrance and an exit. The hall was surrounded by walls, with nothing inside except for the entrance and exit. The young man placed several mirrors in the hall, using the mirrors' reflections to direct sunlight from the entrance to the exit. This way, he could kill the demon and save the princess.

Each mirror in the hall has two reflective surfaces. The way the mirrors are placed ensures that the beam of light always enters at a 45-degree angle, and it can only turn left or right by 90 degrees. Each mirror can rotate, meaning each mirror has two states: one that turns incoming light 90 degrees to the left, and another that turns it 90 degrees to the right. The walls can absorb any sunlight beams, meaning no light can reflect back onto them. Light beams travel in straight lines, and one beam can pass through another without any effect. However, the young man hastily placed the mirrors in the hall, so some mirrors are in the wrong state. This prevents the sunlight from successfully reaching the exit from the entrance, preventing the young man from killing the demon and rescuing the princess. The question is: what is the minimum number of mirrors that need to be changed so that sunlight can successfully travel from the entrance to the exit through the hall, allowing the hero to complete the mission?

Input: The input is a plain text file representing a series of halls. Each hall description starts with a line containing two integers, M and N (3 <= M, N <= 100), separated by a space, indicating the size of the hall with M rows and N columns. The following M lines each contain N characters with no separators. '/' and '\' represent mirrors and their states, '*' is a wall, and '.' represents empty space. The end of the input file is denoted by `M = 0` and `N = 0`.

Output: For each hall, your program should output a single integer on a new line, specifying the minimum number of mirrors that must be changed. If no change in mirror states is needed, output 0. If sunlight cannot reach the exit, output -1.

Sample Input:
```
5 4
****
*\/*
*./.
*..*
*.**
4 4
*.**
*.\*
*\\*
**.*
0 0
```

Sample Output:
```
3
0
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
