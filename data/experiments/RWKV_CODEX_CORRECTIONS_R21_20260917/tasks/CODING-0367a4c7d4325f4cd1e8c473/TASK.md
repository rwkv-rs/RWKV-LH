Loglan is a synthetic language designed to explore certain fundamental linguistic questions, such as the Sapir-Whorf hypothesis. It is grammatically explicit, culturally neutral, and metaphysically economical. It follows a very small set of approximately 200 grammatical rules. 
Loglan sentences are composed of a series of words and names, separated by spaces and ending with a period (.). Loglan words always end with a vowel; names derived from languages end with a consonant. Loglan words are divided into two categories - small words that specify structure, and predicates in the form of ccvcv or cvcv, where 'c' stands for consonant and 'v' stands for a vowel (see the examples below). 
We are considering a subset of Loglan using the following grammar: 
![uva134](https://cdn.luogu.org/upload/pic/49860.png) 
Write a program that reads a series of strings and determines whether they form Loglan sentences.

###### Input
Each Loglan sentence will start on a new line and end with a period (.). Sentences can span multiple lines, and words can be separated by multiple spaces. The input ends with a line containing a single '#'. You can assume all words are correctly formed.

###### Output
The output is "good" or "bad" for each sentence on a new line.

## Input and Output Samples

### Sample Input #1

```
la mutce bunbo mrenu bi ditca.
la fumna bi le mrenu.
djan ga vedma le negro ketpi.
#
```

### Sample Output #1

```
Good
Bad
Good
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
