def format_bytes(num):

    if num is None:
        return "0 B"

    for unit in ["B", "KB", "MB", "GB", "TB"]:

        if num < 1024:
            return f"{num:.2f} {unit}"

        num /= 1024

    return f"{num:.2f} PB"
