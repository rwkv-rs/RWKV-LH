### Brief Description
Given a string (length $\le80$), if it is plaintext, convert it into ciphertext, and if it is ciphertext, convert it into plaintext.  
The plaintext can only contain the following characters: uppercase and lowercase letters, exclamation marks, commas, periods, spaces, colons, semicolons, and question marks (all in English punctuation).  
The encryption method is: convert each character to its corresponding ASCII code, then reverse the entire sequence.  
e.g. For the plaintext `abc`, first convert it to the corresponding ASCII codes: `97 98 99`, remove the spaces: `979899`, reverse the entire sequence to output: `998979`.  
### Input Format
There are multiple sets of data input, each consisting of a line with a string representing either plaintext or ciphertext (self-identification is required).
### Output Format
For each set of data, output a single line as a string representing the answer.

## Input and Output Example

### Input Example #1

```
abc
798999
Have a Nice Day !
```

### Output Example #1

```
998979
cba
332312179862310199501872379231018117927
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
