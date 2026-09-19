A large company wants to monitor the cost of phone calls made by its employees. To achieve this, the PABX system records each call's dialed number (a string of up to 15 digits) and its duration (in minutes). Your task is to write a program to process this data and generate a report based on standard telecommunication charges. International Direct Dialing (IDD) numbers start with two zeros (00), followed by a country code (1–3 digits), and then the subscriber number (4-10 digits). National Direct Dialing (STD) calls start with a zero (0) followed by an area code (1-5 digits) and a subscriber number (4-7 digits). The cost of a call is determined by its destination and duration. Local calls, which start with any digit other than 0, are free of charge.

## Input and Output Format

The input is split into two parts. The first part consists of a table of IDD and STD codes, location names, and prices as follows:
**Code△Location Name＄Price per minute in cents**

Where △ represents a space. Location names have a maximum of 25 characters. This section ends with a line containing six zeros (000000).  
The second part contains logs, represented by a series of lines, each line corresponding to one call, containing the dialed number and duration. The file is terminated by a line containing a single #. The numbers, although spaced at least once apart, are not necessarily listed in order. Phone numbers will not be ambiguous.

###### Output

The output should consist of the dialed number, the destination country or area, the subscriber number, the duration, the cost per minute, and the total cost of the call, as shown below. Local calls are charged at zero. If a number has an invalid code, list the area as "Unknown" with a cost of 1.00.

**Note: The first line of the sample output below is not part of the output; it only shows that the exact format must be followed.**

## Sample Input

### Sample Input #1

```
088925 Broadwood$81
03 Arrowtown$38
0061 Australia$140
000000
031526
22
0061853279 3
0889256287213 122
779760 1
002832769 5
#
```

## Sample Output

```
1
17
51
56
62
69
031526
Arrowtown
1526 22 0.38 8.36
0061853279
Australia 853279 3 1.40 4.20
0889256287213 Broadwood 6287213 122 0.81 98.82
779760
Local
779760 1 0.00 0.00
002832769
Unknown
5
-1.00
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
