# start a fastapi server with uvicorn

import uvicorn

from internal_assistant.main import app
from internal_assistant.settings.settings import settings

# Set log_config=None to not use the uvicorn logging configuration, and
# use ours instead. For reference, see below:
# https://github.com/tiangolo/fastapi/discussions/7457#discussioncomment-5141108
uvicorn.run(app, host="0.0.0.0", port=settings().server.port, log_config=None)
