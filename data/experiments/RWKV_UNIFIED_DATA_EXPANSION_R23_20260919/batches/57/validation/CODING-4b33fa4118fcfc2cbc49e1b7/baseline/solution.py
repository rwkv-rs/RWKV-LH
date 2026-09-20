import sys

def main():
    data = sys.stdin.read().strip().split()
    if not data:
        return
    T = int(data[0])
    C = int(data[1])
    targets = list(map(int, data[2:2+T]))
    commands = data[2+T]
    
    def simulate(commands):
        pos = 0
        hits = 0
        hit_set = set()
        for cmd in commands:
            if cmd == 'L':
                pos -= 1
            elif cmd == 'R':
                pos += 1
            elif cmd == 'F':
                if pos in targets and pos not in hit_set:
                    hits += 1
                    hit_set.add(pos)
        return hits
    
    best = simulate(commands)
    
    for i in range(C):
        new_cmds = commands[:i] + commands[i+1:]
        best = max(best, simulate(new_cmds))
    
    print(best)

if __name__ == "__main__":
    main()
