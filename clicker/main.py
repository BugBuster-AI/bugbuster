import os
import sys

ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from src.main import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn
    from src.core.config import UVICORN_PORT

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=UVICORN_PORT,
        reload=False,
        workers=1,
        proxy_headers=True,
        ws_ping_interval=25,
        ws_ping_timeout=120,
        timeout_keep_alive=120,
    )
