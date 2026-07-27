import logging
import sys


def error_message_detail(error: Exception, error_detail: sys) -> str:
    """
    Builds a detailed error string: file name, line number, and the original message.
    Requires the actual exception object (not just its string) to read the traceback.
    """
    _, _, exc_tb = error_detail.exc_info()
    file_name = exc_tb.tb_frame.f_code.co_filename
    line_number = exc_tb.tb_lineno
    error_message = (
        f"Error occurred in python script: [{file_name}] "
        f"at line number [{line_number}]: {str(error)}"
    )
    logging.error(error_message)
    return error_message


class AgentException(Exception):
    """
    Custom exception for the book-cover-workflow agent.
    Wraps any caught exception with file/line context so tracebacks
    inside LangGraph nodes are actually debuggable.

    Usage:
        try:
            ...
        except Exception as e:
            raise AgentException(e, sys) from e
    """

    def __init__(self, error: Exception, error_detail: sys):
        super().__init__(str(error))
        self.error_message = error_message_detail(error, error_detail)

    def __str__(self) -> str:
        return self.error_message