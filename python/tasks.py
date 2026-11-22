"""Background task helpers shared by the app and the BLE layer."""
import asyncio


# Strong references to fire-and-forget tasks (asyncio keeps only weak ones, so tasks could be GC'd).
background_tasks: set = set()

def spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task

async def run_forever(name: str, factory, restart_delay: float = 5):
    """Supervisor: restarts a background loop if it ever crashes or returns."""
    while True:
        try:
            await factory()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"❌ {name} crashed: {e}. Restarting in {restart_delay}s...")
        await asyncio.sleep(restart_delay)
