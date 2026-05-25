import msvcrt
import sys
import unicodedata

def get_input(prompt="你: "):
    """读取用户输入，按 Esc 返回 None，按 Enter 提交。"""
    print(prompt, end="", flush=True)
    chars = []
    while True:
        ch = msvcrt.getwch()
        if ch == '\x1b':
            print("\n[已打断]")
            return None
        elif ch == '\r' or ch == '\n':
            print()
            break
        elif ch == '\x08':
            if chars:
                c = chars.pop()
                w = 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
                sys.stdout.write('\b' * w + ' ' * w + '\b' * w)
                sys.stdout.flush()
        else:
            chars.append(ch)
            sys.stdout.write(ch)
            sys.stdout.flush()
    return ''.join(chars)
