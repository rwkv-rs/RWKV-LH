**Problem Description**  
A data stream is a real-time, continuous, and ordered sequence of entries. Some examples include sensor data, internet transactions, financial quotes, online auctions, transaction logs, web usage logs, and telephone call records. Similarly, queries on data streams should run continuously at specified intervals, producing new results as new data is generated. For example, a temperature monitoring system in a factory warehouse could perform queries like:
- Query 1: "Retrieve the highest temperature in the past 5 minutes, every five minutes."
- Query 2: "Return the average temperature on each floor for the past 10 minutes."

We have developed a data stream management system called Argus to handle queries on data streams. Users can register queries in Argus. It will continuously execute the queries on the ever-changing data and return results to the respective users at the required frequencies.

For Argus, queries are registered using the following instruction:
`Register Q_num Period`  
- `Q_num` (0 < Q_num <= 3000) is the query’s ID number.
- `Period` (0 < Period <= 3000) is the interval between the returns of two consecutive query results. The first result is returned after registering and then every `Period` seconds thereafter.

Several different queries are registered on Argus, each with a unique `Q_num`. Your task is to determine the first K queries to return results. If two or more queries return results simultaneously, they should be ordered in ascending order of their `Q_nums`.

**Input**  
The first section of the input consists of registration instructions on Argus, with one instruction per line. The number of instructions does not exceed 1000, and all instructions start simultaneously. This section ends with a "#".  
The second section contains a single line with a positive integer K (<= 10000).

**Output**  
Output the `Q_num` of the first K queries to return results, each on a new line.

**Sample Input**  
```
Register 2004 200
Register 2005 300
#
5
```

**Sample Output**  
```
2004
2005
2004
2004
2005
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
