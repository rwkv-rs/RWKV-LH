**[Road Query]**

**[Background]**  
The internet now offers a variety of interactive maps, allowing users to view flat maps and "zoom in" to see specific streets or even buildings. For example, the city of San Jose may appear on a map of California or on a map of Santa Clara County. You have a large number of maps and need to assemble and design an interactive map, so you need to handle queries for locations with different levels of detail.

**[Problem]**

There are `n` maps (with known names and the coordinates of two endpoints of one diagonal) and `m` place names (with known names and coordinates), as well as `q` queries.

Each map is a rectangle with edges parallel to the coordinate axes, and the aspect ratio is defined as height divided by width. Each query contains a place name and a detail level `i`. Maps with the same area all belong to the same detail level.  

Assume that among the maps containing this place name, there are `k` different areas, then the valid detail levels are 1~k (where 1 is the least detailed and k is the most detailed, with smaller areas being more detailed).
- If there is more than one map at detail level `i`, output the one with the center closest to the query location.
- If there's a tie, choose the map with an aspect ratio closest to 0.75 (this is the ratio of a web browser).
- If there's still a tie, the map with the bottom right corner coordinates farthest from the query location is chosen (corresponding to the least scrolling).
- If there's still a tie, choose the map with the smallest x-coordinate.
- If the query place name does not exist or is not contained in any map, or the total number of maps containing it exceeds `i`, the query is invalid (if exists, also output the name of the most detailed map containing it).

**[Input]**  
The input file consists of a set of maps, locations, and requests, in the following order:

- The first line contains the word 'MAPS', indicating the start of map inputs, followed by several lines each containing the name of a map (a single string without spaces) and coordinates of two endpoints of a diagonal x1, y1, x2, y2 (maps are unique)
- When a lone line with 'LOCATIONS' is encountered, stop inputting maps, and the following lines will start inputting location names (a single string without spaces) and location coordinates x, y
- When a lone line with 'REQUESTS' is encountered, stop inputting locations, and the following lines will start inputting a query name (a single string without spaces) and a positive integer representing the required level of detail for that location
- When a lone line with 'END' is encountered, stop inputting

The results for processing valid requests include the name of the map and the coordinates of the given location. (See sample)

Invalid queries include unknown location names, locations not appearing in any map, or locations exceeding the level restriction.

**[Output]**  
After each request, output (with specific strings in italics):

1. If the city does not exist, output "_name_ at detail level _level_ unknown location"

2. If it exists, output: "_name_ at detail level _level_"

3. Invalid requests:

- If no map contains that location, output "no map contains that location"

- If a map contains that location but not at the corresponding detail level, output the best suitable map name "no map at that detail level; using _MapName_"

- If a map with the corresponding detail level contains the city, output the map name to be used, "using _MapName_"

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
