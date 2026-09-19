Given a Boolean algebraic expression consisting of uppercase and lowercase letters (variables), `|`, and `~`, determine how many ways there are to assign values to the given variables such that the expression evaluates to `True`.

Notes:
- `a|b` represents $a \vee b$, which is equivalent to `a || b` in C++.
- `~a` represents $\neg a$, which is equivalent to `(!a)` in C++.
- Variables are single letters only.

## Problem Description

The Boolean satisfiability problem (SAT) is known to be a very hard problem in computer science. In this problem, you are given a Boolean formula, and you need to find out if the variables of a given formula can be consistently replaced by the values true or false in such a way that the formula evaluates to true. SAT is known to be NP-complete. Moreover, it is NP-complete even in the case of $3-CNF$ formula ($3-SAT$). However, for example, the SAT problem for $2-CNF$ formulae ($2-SAT$) is in $P$.

$#SAT$ is the extension of the SAT problem. In this problem, you need to check if it is possible and count the number of ways to assign values to variables. This problem is known to be $#P-complete$ even for $2-CNF$ formulae. We ask you to solve $#1-DNF-SAT$, which is the $#SAT$ problem for $1-DNF$ formulae.

You are given a Boolean formula in $1-DNF$ form. It means that it is a disjunction (logical or) of one or more clauses, each clause is exactly one literal, each literal is either a variable or its negation (logical not).

Formally:
- $〈formula〉 ::= 〈clause〉 | 〈formula〉 ∨ 〈clause〉$
- $〈clause〉 ::= 〈literal〉$
- $〈literal〉 ::= 〈variable〉 | ¬ 〈variable〉$
- $〈variable〉 ::= A . . . Z | a . . . z$

Your task is to find the number of ways to replace all variables with values true and false (all occurrences of the same variable should be replaced with the same value), such that the formula evaluates to true.

## Input Format

The only line of the input file contains a logical formula in $1-DNF$ form (not longer than $1000$ symbols). Logical operations are represented by `|` (disjunction) and `~` (negation). The variables are `A` . . . `Z` and `a` . . . `z` (uppercase and lowercase letters are different variables). The formula contains neither spaces nor other characters not mentioned in the grammar.

## Output Format

Output a single integer -- the answer for the $#SAT$ problem for the given formula.

## Sample Input and Output

### Input Sample #1
```
a
```

### Output Sample #1
```
1
```

### Input Sample #2
```
B|~B
```

### Output Sample #2
```
2
```

### Input Sample #3
```
c|~C
```

### Output Sample #3
```
3
```

### Input Sample #4
```
i|c|p|c
```

### Output Sample #4
```
7
```

## Notes/Hints

Time limit: 3 s, Memory limit: 512 MB.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
