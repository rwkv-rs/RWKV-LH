You are given a set of letters, and the challenge is to determine how many distinct words can be formed using these letters. The aim is to resolve this problem by writing a program.

## Input

The input is divided into two parts. The first part is a dictionary with fewer than 1000 lines, containing words. Each line includes up to 10 words, arranged in alphabetical order. This part ends with a "#" character.

Following the dictionary, there are several word puzzle data entries, each on a separate line. Each puzzle consists of one or more lowercase letters separated by spaces. Your task is to use some or all of these letters to form words found in the dictionary. The list of puzzles is terminated by a single line of "#".

## Output

For each puzzle line in the input, you should generate one output line, which contains the number of distinct words from the dictionary that can be formed using the letters from the puzzle line.

Note: Each letter may only be used as many times as it appears in the puzzle line. For example, the puzzle "u l l" could create the word "lul" but not "lull".

## Input and Output Example

### Input #1

```
ant
bee
cat
dog
ewe
fly
gnu
#
bew
bbeeww
tancugd
#
```

### Output #1

```
0
2
3
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
