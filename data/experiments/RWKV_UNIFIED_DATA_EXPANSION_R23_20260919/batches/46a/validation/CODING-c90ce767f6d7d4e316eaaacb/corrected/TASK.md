The Public Relations (PR) office is looking for an easier way to compile information for their black book, a list of all faculty and staff. Currently, each department submits a list of their faculty that is then compiled by PR into an alphabetically sorted list by last name. PR is now searching for a program that can combine these faculty lists into a format that can be used for the black book. All lists are stored in text files. Each department's file is sorted by last name. The program should take these individually sorted files and combine them into a single sorted file in the format shown below.

## Input

The input file will begin with a number (between 2 and 12) indicating the number of departments whose lists your program should sort and write to the output file. After the first line, there will be a series of groups of lines. The first line of each group contains a department name, followed by several lines containing the data to be sorted. The information is provided in the following order: title, first name, last name, street address, home phone, work phone, and campus box. Information is separated by commas. Blank lines separate groups of lines. There will be the same number of department headers and data sets as the number reported in the first line.

### Each record saved in the output file should be formatted as follows:

--------------------------------------
<Title> <First Name> <Last Name>
<Home Address>
Department: <Department>
Home Phone: <Home Phone>
Work Phone: <Work Phone>
Campus Box: <Campus Box>

The dashed line should appear at the top of each record. The characters “<” and “>” indicate where a field should be placed. Note the spacing. You can assume that all the input files are syntactically correct without extra spaces. Thus, PR expects the requested data to be in the correct syntax.

## Input and Output Examples

### Input Example #1

```
2
English Department
Dr.,Tom,Davis,Anystreet USA,555-2832,555-2423,823
Mrs.,Jessica,Lembeck,Center Street,555-2543,555-8584,928
Computer Science
Mr.,John,Euler,East Pleasure,555-1432,555-2343,126
```

### Output Example #1

```
----------------------------------------
Dr. Tom Davis
Anystreet USA
Department: English Department
Home Phone: 555-2832
Work Phone: 555-2423
Campus Box: 823
----------------------------------------
Mr. John Euler
East Pleasure
Department: Computer Science
Home Phone: 555-1432
Work Phone: 555-2343
Campus Box: 126
----------------------------------------
Mrs. Jessica Lembeck
Center Street
Department: English Department
Home Phone: 555-2543
Work Phone: 555-8584
Campus Box: 928
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
