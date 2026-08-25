import asyncio
from datetime import datetime, timezone

from .retrieval import index_changed

class WatchState:
    def __init__(self):
        self.running = False
        self.last_scan = None
        self.last_result = None
        self.last_error = None

    def as_dict(self):
        return {
            "running": self.running,
            "last_scan": self.last_scan,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }

async def watch_loop(db, s, state):
    state.running = True
    await asyncio.sleep(2)
    try:
        while True:
            try:
                result = await index_changed(db, s)
                state.last_scan = datetime.now(timezone.utc).isoformat()
                state.last_result = result
                state.last_error = None
            except Exception as exc:
                state.last_error = str(exc)
            await asyncio.sleep(s.watch_interval_seconds)
    except asyncio.CancelledError:
        raise
    finally:
        state.running = False
