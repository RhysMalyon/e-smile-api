import contextvars
import logging
import sys

# 1. Define a thread/async-safe context variable to store the ID
correlation_id_var = contextvars.ContextVar("correlation_id", default="-")


# 2. Create a Filter to dynamically inject the context variable into the log record
class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        # Automatically attaches correlation_id to every log record
        record.correlation_id = correlation_id_var.get()
        return True


def setup_logging():
    handler = logging.StreamHandler(sys.stdout)

    handler.addFilter(CorrelationIdFilter())

    formatter = logging.Formatter(
        "%(asctime)s (%(correlation_id)s): %(levelname)s - %(name)s - %(message)s"
    )

    handler.setFormatter(formatter)

    # Root logger setup
    logger = logging.getLogger()

    logger.setLevel(logging.INFO)

    # Clear existing handlers
    for existing_handler in logger.handlers[:]:
        logger.removeHandler(existing_handler)
        existing_handler.close()

    logger.addHandler(handler)

    # Clear default handlers on target loggers
    uvicorn_loggers = ("uvicorn", "uvicorn.error", "uvicorn.access")

    for logger_name in uvicorn_loggers:
        uvicorn_logger = logging.getLogger(logger_name)

        for uvicorn_handler in uvicorn_logger.handlers[:]:
            uvicorn_logger.removeHandler(uvicorn_handler)
            uvicorn_handler.close()

        uvicorn_logger.propagate = True
