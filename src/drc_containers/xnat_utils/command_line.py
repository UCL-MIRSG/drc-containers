import re


def string_to_list(arg: str) -> list[str]:
    """Convert a delimited string into list of strings. The delimiter is any
    combination of whitespace characters, commas or semicolons. Empty strings
    are removed from the list

    Args:
        arg: delimited string

    Returns:
        list of strings extracted from the input string
    """
    return [a for a in re.split(r"[;,\s]+", arg) if a]
