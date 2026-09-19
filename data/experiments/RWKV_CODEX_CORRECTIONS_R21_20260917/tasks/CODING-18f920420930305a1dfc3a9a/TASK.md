Kobayashi is a programmer, and inevitably, Kanna has developed a strong interest in this human "magic." So, Kobayashi starts teaching her OI (Olympiad in Informatics).

![Segment Tree](https://cdn.luogu.com.cn/upload/pic/8043.png)

Today, Kanna learned a magical technique called a segment tree, which can maintain information about a segment and is a very powerful tool. Kanna tried to write a segment tree that maintains the sum of intervals. Since she doesn't know how to use lazy tags, she modifies all interval addition operations by brute force. The specific code is as follows:

```cpp
struct Segment_Tree{
#define lson (o<<1)
#define rson (o<<1|1)
    int sumv[N<<2],minv[N<<2];
    inline void pushup(int o){sumv[o]=sumv[lson]+sumv[rson];}
    inline void build(int o,int l,int r){
        if(l==r){sumv[o]=a[l];return;}
        int mid=(l+r)>>1;
        build(lson,l,mid);build(rson,mid+1,r);
        pushup(o);
    }
    inline void change(int o,int l,int r,int q,int v){
        if(l==r){sumv[o]+=v;return;}
        int mid=(l+r)>>1;
        if(q<=mid)change(lson,l,mid,q,v);
        else change(rson,mid+1,r,q,v);
        pushup(o);
    }
}T;
```

When modifying, she writes:

```cpp
for(int i=l;i<=r;i++)T.change(1,1,n,i,addv);
```

Obviously, each node in this segment tree has a value, which is the sum of the interval it manages.

Kanna is a thoughtful child, so she suddenly thought of a problem:

If after each interval addition operation on the segment tree, starting from the root node, a child node is chosen probabilistically to enter until reaching a leaf node, and the values of the nodes passed along the way are accumulated, what is the expected value that can be obtained?

Kanna will give you a value $qwq$, ensuring that the probability you calculate multiplied by $qwq$ is an integer.

This problem is too simple, and the clever Kanna solved it in an instant.

Now she wants to ask you, can you solve this problem?

## Input Format

The first line contains three integers $n, m, qwq$, representing the length of the original sequence maintained by the segment tree, the number of queries, and the denominator.

The second line contains $n$ numbers, representing the original sequence.

The next $m$ lines, each containing three numbers $l, r, x$, indicate adding $x$ to the interval $[l, r]$.

## Output Format

A total of $m$ lines, representing the expected value multiplied by $qwq$.

## Sample Input and Output

### Input Sample #1

```
8 2 1
1 2 3 4 5 6 7 8
1 3 4
1 8 2
```

### Output Sample #1

```
90
120
```

## Notes/Hints

For 30% of the data, it is guaranteed that $1 \leq n, m \leq 100$.

For 70% of the data, it is guaranteed that $1 \leq n, m \leq 10^5$.

For 100% of the data, it is guaranteed that $1 \leq n, m \leq 10^6$.

$-1000 \leq a_i, x \leq 1000$.

The input will be given via stdin and the output should be printed to stdout by your code.

Now solve the problem by providing the code.
