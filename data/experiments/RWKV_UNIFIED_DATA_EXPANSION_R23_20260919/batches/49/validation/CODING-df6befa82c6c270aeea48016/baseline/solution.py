import sys

def solve():
    data = sys.stdin.read().splitlines()
    if not data:
        print(-1)
        return
    n, m, k = map(int, data[0].split())
    grid = [list(line.rstrip()) for line in data[1:1+n]]
    commands = data[1+n].strip()
    if len(commands) != k:
        print(-1)
        return
    dirs = {'L': (0, -1), 'R': (0, 1), 'U': (-1, 0), 'D': (1, 0)}
    exit_pos = None
    for i in range(n):
        for j in range(m):
            if grid[i][j] == 'E':
                exit_pos = (i, j)
                break
        if exit_pos:
            break
    if exit_pos is None:
        print(-1)
        return
    exit_i, exit_j = exit_pos
    for start_i in range(n):
        for start_j in range(m):
            if grid[start_i][start_j] == '#':
                continue
            x, y = start_i, start_j
            for cmd in commands:
                dx, dy = dirs.get(cmd, (0, 0))
                nx, ny = x + dx, y + dy
                if 0 <= nx < n and 0 <= ny < m and grid[nx][ny] != '#':
                    x, y = nx, ny
            if (x, y) == (exit_i, exit_j):
                print(len(commands))
                return
    print(-1)

if __name__ == "__main__":
    solve()
