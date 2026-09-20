import sys

def main():
    data = sys.stdin.read().strip().splitlines()
    if not data:
        print("No")
        return
    m, n, k = map(int, data[0].split())
    octocube = []
    for i in range(1, 1 + k):
        octocube.append(data[i].strip())
    # Build adjacency graph of cells
    adj = [[] for _ in range(n * m * k)]
    for i in range(k):
        for r in range(n):
            for c in range(m):
                if octocube[i][r][c] == 'x':
                    idx = i * n * m + r * m + c
                    # Check neighbors in the same slice
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < n and 0 <= nc < m and octocube[i][nr][nc] == 'x':
                            adj[idx].append(i * n * m + nr * m + nc)
                    # Check neighbors in adjacent slices
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < n and 0 <= nc < m:
                            if i > 0 and octocube[i-1][nr][nc] == 'x':
                                adj[idx].append((i-1) * n * m + nr * m + nc)
                            if i < k-1 and octocube[i+1][nr][nc] == 'x':
                                adj[idx].append((i+1) * n * m + nr * m + nc)
    # Check if the graph is connected
    visited = [False] * (n * m * k)
    stack = [0]
    visited[0] = True
    while stack:
        v = stack.pop()
        for w in adj[v]:
            if not visited[w]:
                visited[w] = True
                stack.append(w)
    if sum(visited) != n * m * k:
        print("No")
        return
    # Check if the graph is a tree (connected and has exactly n*m*k - 1 edges)
    if len(adj) != n * m * k or sum(len(adj[v]) for v in range(n * m * k)) != 2 * (n * m * k - 1):
        print("No")
        return
    # Check if the graph is planar (can be embedded in 3D space)
    # For a tree, planarity is guaranteed if it is a tree (no cycles)
    print("Yes")
if __name__ == "__main__":
    main()
