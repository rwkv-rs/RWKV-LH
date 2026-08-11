class TaskQueue:
    def __init__(self):
        self._items = []

    def add(self, task_id, priority):
        self._items.append((priority, task_id))

    def pop(self):
        if not self._items:
            raise IndexError('empty')
        return self._items.pop()[1]
