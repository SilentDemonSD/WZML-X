from sys import stderr
from traceback import format_exception


def send_unhandled_exception(exc_type, exc_value, exc_traceback):
    print("".join(format_exception(exc_type, exc_value, exc_traceback)), file=stderr)


def send_async_exception(context):
    exc = context.get("exception")
    if exc is not None:
        print(
            "".join(format_exception(type(exc), exc, exc.__traceback__)),
            file=stderr,
        )
    elif context.get("message"):
        print(context["message"], file=stderr)
