import asyncio
import inspect
import random
import time


async def gen1():

    for i in range(10):
        yield str(f"Gen1 {i}")
        await asyncio.sleep(random.uniform(0, 0.5))

    yield gen3()


async def gen2():
    for i in range(10):
        yield str(f"Gen2 {i}")
        # yield asyncio.create_task(asyncio.sleep(random.uniform(0, 2)))
        # await asyncio.sleep(random.uniform(0, 2))

    # yield gen3()


async def gen3():
    for i in range(10):
        yield str(f"Gen3 {i}")


async def genboth():
    yield gen1()

    yield gen2()


class TaskRunner:
    tasks = []

    async def process(self, result):
        if inspect.isasyncgen(result):
            async for value in result:
                self.tasks.append(asyncio.create_task(self.process(value)))
            # asyncio.create_task(self.process(i)) async for i in result
            # await asyncio.gather(*tasks)
            # async for value in result:

            #     tasks.append(asyncio.create_task(process(value)))

        elif isinstance(result, str):
            print(result)
        elif inspect.iscoroutine(result):
            self.tasks.append(result)


async def runall():
    start = time.perf_counter()
    generator = genboth()
    # async for value in generator:
    #     if inspect.isasyncgen(value):
    #         async for v2 in value:
    #             print(v2)
    #     print(value)
    runner = TaskRunner()
    await runner.process(generator)
    await asyncio.gather(*runner.tasks)

    duration = int((time.perf_counter() - start) * 1000)
    print(f"Ran in {duration}ms")


asyncio.run(runall())
