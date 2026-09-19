Expression trees, B/B* trees, red-black trees, quadtrees, PQ trees... trees have played an important role in many fields of computer science. Some problems explicitly indicate the use of tree structures in their names, like the "monkey and banana" problem traditionally used in AI planning. Other problems, although using tree structures, do not explicitly mention them in their names, like Huffman coding.

This problem requires determining whether two people have a familial relationship within a genealogy.

Given a series of "child-father" name pairs as a genealogy, in each pair, the first is the child, and the second is the father (single parent). A series of name pairs to be checked is also given, representing the names of two people. You need to write a program to determine whether the two names in the pair exhibit a familial relationship within the genealogy. If they do have a familial relationship, you must output what kind of relationship it is. The relationship between a student and a mentor in a university can be considered a single-parent lineage example (we assume each student has only one mentor, with no co-mentorship).

In this problem, the "child-father" pair p q indicates that p is the child of q. During the determination of the name relationships, we have the following inductive definition:

- p is the 0th descendant of q if and only if there exists a "child-father" pair p q in the input sequence indicating a "child-father" relationship.
- p is the kth descendant of q if and only if r is the (k - 1)th descendant of q, and there exists a "child-father" pair p r in the input sequence indicating a "child-father" relationship.

For this problem, p and q can have only one of the following four types of relationships:

1. Child relationship—which includes grandchild, great-grandchild, great-great-grandchild, etc.
   According to the definition, p is the "child" of q if and only if there exists a "child-father" pair p q in the input sequence indicating their "child-father" relationship (i.e., p is the 0th descendant of q); p is the "grandchild" of q if and only if p is the 1st descendant of q; and so on: p is q's (n + 1)th descendant.

2. Parent relationship—which includes grandparent, great-grandparent, great-great-grandparent, etc.
   The parent relationship is defined correspondingly to the child relationship mentioned above.

3. Cousin—0th cousin, 1st cousin, 2nd cousin, etc. Cousins have generational gaps: skipped by one generation, two generations, three generations, etc.
   (Note: American cousin relationships differ significantly from those in Chinese. The "nth cousin" denotes how many generations the older of the two individuals is from the closest common ancestor, minus one. For instance, you and an uncle/aunt (your parent's sibling) share a common ancestor with your grandparent, making you 0th cousins; you and a cousin (your uncle/aunt's child) share a 1st cousin relationship because their closest common ancestor is also grandparent; with your great-aunt's child, you would have a 2nd cousin relationship. If two cousins differ by m generations, it is expressed as "cousin removed m.")

4. Sibling—"0th cousins removed 0 times" are considered "siblings" (they share a common parent).

# The Input
## Input
The input consists of a series of name pairs, each pair occupying a distinct line. In each pair, names are composed of lowercase letters and dots (e.g., sometimes used to separate first and last names). Names in a pair are separated by one or more spaces. When "no.child" appears as the first name of a name pair, it signifies the end of "child-father" pair input. This terminator is only used to separate the "child-father" pairs from the query pairs and should not be processed as a "child-father" pair by the program. There will not be any cyclic relationships in the input, i.e., no name p can simultaneously be both a descendant and an ancestor of name q.

After the "child-father" pairs are the query pairs, formatted in the same way, where each query pair consists of names composed of lowercase letters and dots, separated by one or more spaces. The input for query pairs ends with EOF.

There will be a maximum of 300 different names in total (including "child-father" pairs and query pairs). All names are shorter than 31 characters. There will be a maximum of 100 query pairs.

# The Output
## Output
For each query name pair, output the relationship between p and q in the following format:

    child, grandchild, great-grandchild, great-great-grandchild, etc.
    parent, grandparent, great-grandparent, great-great-grandparent, etc.
    sibling
    n cousin removed m
    no relation

If a "m cousin" is removed by 0 generations, only print "m cousin"; that is, "removed 0" should not appear in the output. Do not add suffixes like "st," "nd," "rd," or "th" to any number.

# Sample Input
## Input Example

```
alonzo.church oswald.veblen
stephen.kleene alonzo.church
dana.scott alonzo.church
martin.davis alonzo.church
pat.fischer hartley.rogers
mike.paterson david.park
dennis.ritchie pat.fischer
hartley.rogers alonzo.church
les.valiant mike.paterson
bob.constable stephen.kleene
david.park hartley.rogers
no.child no.parent
stephen.kleene bob.constable
hartley.rogers stephen.kleene
les.valiant alonzo.church
les.valiant dennis.ritchie
dennis.ritchie les.valiant
pat.fischer michael.rabin
```

# Sample Output
## Output Example

```
parent
sibling
great great grand child
1 cousin removed 1
1 cousin removed 1
no relation
```
```

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
