import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Generic, List, Optional, TypeVar

from optypes.op_types import UserDetails

T = TypeVar("T")  # Input type
R = TypeVar("R")  # Return type


class AsyncExecutor(Generic[T, R]):
    """
    Use this class BEFORE sending to something like run_command_async or run_multiple_commands.
    This class let's us control the concurrency to not overload 1Password (and get rate limited)
    While the client handler allows us to actually run the subcommands.
    """
    def __init__(self, max_concurrent_tasks: Optional[int] = None):
        """
        Initializes the AsyncExecutor.

        Args:
            max_concurrent_tasks (Optional[int]): Maximum number of concurrent tasks. Defaults to 5.
        """
        self.max_concurrent_tasks = max_concurrent_tasks or 5
        self.semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

    async def execute(
        self,
        tasks: List[T],
        task_func: Callable[[T], Awaitable[R]],
        *args,
        **kwargs,
    ) -> List[Optional[R]]:
        """
        Executes tasks concurrently using asyncio with a semaphore to limit concurrency.

        Args:
            tasks (List[T]): A list of task inputs.
            task_func (Callable[[T], Awaitable[R]]): The asynchronous function to execute for each task.
            *args: Additional positional arguments to pass to task_func.
            **kwargs: Additional keyword arguments to pass to task_func.

        Returns:
            List[Optional[R]]: A list of results from the executed tasks.
        """
        logging.info(
            f"Processing {len(tasks)} tasks with up to {self.max_concurrent_tasks} concurrent tasks."
        )

        async def sem_task(task: T) -> Optional[R]:
            async with self.semaphore:
                try:
                    result = await task_func(task, *args, **kwargs)
                    return result
                except Exception as e:
                    logging.error(f"Error processing task {task}: {e}")
                    return None

        coroutines: List[Awaitable[Optional[R]]] = [
            sem_task(task) for task in tasks
        ]

        results: List[Optional[R]] = await asyncio.gather(
            *coroutines, return_exceptions=False
        )

        logging.info("All tasks have been processed.")
        return results


def chunk_list(data: List[Any], chunk_size: int) -> List[List[Any]]:
    return [data[i: i + chunk_size] for i in range(0, len(data), chunk_size)]


async def handle_rate_limit_backoff(rate_limit_hit, backoff_attempts):
    """Handles rate limit backoff with exponential delay."""
    if rate_limit_hit:
        backoff_time = min(60, (2**backoff_attempts))
        print(
            f"Rate limit hit! Pausing for {backoff_time} seconds before retrying..."
        )
        await asyncio.sleep(backoff_time)
        return backoff_attempts + 1, False, 0
    return backoff_attempts, rate_limit_hit, 0


def command(command_path: str, args: list, options: list):
    def decorator(func):
        func.command_path = command_path
        func.argument_specs = args
        func.option_specs = options

        return func

    return decorator


async def async_input(prompt: str = "") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: input(prompt))


def run_async(coro: Awaitable[Any]) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If there's a running loop, schedule the coroutine and return the task
        # make mypy ignore it idk
        task = asyncio.create_task(coro)
        return task
    else:
        # If no loop is running, create a new event loop and run the coroutine
        return asyncio.run(coro)
