import asyncio


async def background_task():
    while True:
        await asyncio.sleep(1)
        raise ValueError("Error in background task")


async def main():
    # not raise error
    task = asyncio.create_task(background_task())
    # raise error
    # asyncio.create_task(background_task())

    while True:
        await asyncio.sleep(1)
        print("Main task is running")


if __name__ == "__main__":
    asyncio.run(main())
