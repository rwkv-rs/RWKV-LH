class TaskQueue:
    def __init__(self): self._items=[]
    def add(self, task_id, priority): self._items.append((priority,task_id))
    def pop(self): return self._items.pop()[1]
