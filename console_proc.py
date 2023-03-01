"""functions for console output"""


_loading_chars = '-\\|/'
_char_pos = 0


def print_loading():
    """Prints loading stick"""
    global _char_pos
    _char_pos = (_char_pos + 1) % len(_loading_chars)
    print("\r", end=" ")
    print(_loading_chars[_char_pos], end=" ")


if __name__ == "__main__":
    import time

    while True:
        print_loading()
        time.sleep(0.1)
