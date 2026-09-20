In the Wisconsin dairy farms, it is customary for accountants to brand cows with consecutive numbers. However, cows themselves do not find this system convenient; they prefer to call their companions by their favorite names rather than phrases like "C'mon, #4364, get along." Please write a program to help the poor cowhands translate a cow's brand number into a possible name. Since cows now have mobile phones, use the standard keypad layout to translate numbers into letters (excluding "Q" and "Z"):

```
2: A,B,C     5: J,K,L    8: T,U,V
3: D,E,F     6: M,N,O    9: W,X,Y
4: G,H,I     7: P,R,S
```

Acceptable names are stored in a file called "dict.txt," which contains less than 5,000 (specifically, 4617) acceptable cow names. (All names are in uppercase and sorted lexicographically.) Please read the cow's number and return those names that can be translated from the number and are in the dictionary. For example, the number 4734 can produce the following names: GPDG GPDH GPDI GPEG GPEH GPEI GPFG GPFH GPFI GRDG GRDH GRDI GREG GREH GREI GRFG GRFH GRFI GSDG GSDH GSDI GSEG GSEH GSEI GSFG GSFH GSFI HPDG HPDH HPDI HPEG HPEH HPEI HPFG HPFH HPFI HRDG HRDH HRDI HREG HREH HREI HRFG HRFH HRFI HSDG HSDH HSDI HSEG HSEH HSEI HSFG HSFH HSFI IPDG IPDH IPDI IPEG IPEH IPEI IPFG IPFH IPFI IRDG IRDH IRDI IREG IREH IREI IRFG IRFH IRFI ISDG ISDH ISDI ISEG ISEH ISEI ISFG ISFH ISFI. Coincidentally, out of the 81, only "GREG" is valid (in the dictionary).

Write a program to print out all valid names for a given number, or output NONE if there are none. The number may have up to 12 digits.

## Input Format

The first line contains a number (length may range from 1 to 12).

The next 4617 lines, each containing a string representing an acceptable name.

## Output Format

(file namenum.out)

Output a non-repeating list of valid names in lexicographical order, one name per line. If there are no valid names, output 'NONE'.

## Sample Input and Output

### Sample Input #1

```
4734
NMSL
GREG
LSDC
....(too many to list)
```

### Sample Output #1

```
GREG
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
