"""Bounded project stages without a batch barrier or cancellation of live requests.

This schedules offline work only. Agent decisions, tools, admission rules and
episode acceptance remain the responsibility of their existing production APIs.
Callbacks return None for a documented rejected candidate. Unexpected failures
stop new authoring and drain already started work before propagating the error.
"""
import asyncio


async def run_pipeline(indices, *, author, admit, execute, author_workers=32,
                       admission_workers=8, execution_workers=32, buffer_size=32,
                       stop=None, observe=None):
    for count in (author_workers, admission_workers, execution_workers, buffer_size):
        if type(count) is not int or count < 1:
            raise ValueError('positive pipeline worker and buffer counts required')
    iterator = iter(indices)
    authored = asyncio.Queue(maxsize=buffer_size)
    admitted = asyncio.Queue(maxsize=buffer_size)
    end = object()
    errors = []
    totals = {stage: {'started': 0, 'finished': 0, 'rejected': 0, 'failed': 0}
              for stage in ('author', 'admit', 'execute')}

    async def call(stage, callback, item):
        totals[stage]['started'] += 1
        try:
            if observe: observe(stage, 'started', item)
            value = await callback(item)
            if value is None: totals[stage]['rejected'] += 1
            return value
        except Exception as error:
            errors.append(error)
            totals[stage]['failed'] += 1
            return None
        finally:
            totals[stage]['finished'] += 1
            try:
                if observe: observe(stage, 'finished', item)
            except Exception as error:
                errors.append(error)

    async def produce():
        while not errors and not (stop and stop()):
            try: index = next(iterator)
            except StopIteration: return
            value = await call('author', author, index)
            if value is not None: await authored.put(value)

    async def check():
        while True:
            item = await authored.get()
            if item is end: return
            value = await call('admit', admit, item)
            if value is not None: await admitted.put(value)

    async def run():
        while True:
            item = await admitted.get()
            if item is end: return
            await call('execute', execute, item)

    checking = [asyncio.create_task(check()) for _ in range(admission_workers)]
    running = [asyncio.create_task(run()) for _ in range(execution_workers)]
    await asyncio.gather(*(produce() for _ in range(author_workers)))
    for _ in checking: await authored.put(end)
    await asyncio.gather(*checking)
    for _ in running: await admitted.put(end)
    await asyncio.gather(*running)
    if errors: raise errors[0]
    return totals
