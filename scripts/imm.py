#!/usr/bin/env python3
"""
Infinitely Many Meanings (IMM) - encode/decode for LLM jailbreaking.
Usage:
  python3 imm.py encode "Your message here"
  python3 imm.py decode "[73, 32, 97, ...]"
"""
import sys
import ast


def encode(pt):
    return [ord(c) for c in pt]


def decode(ct):
    return ''.join([chr(n) for n in ct])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: imm.py encode <message>  OR  imm.py decode <int_list>")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "encode":
        msg = " ".join(sys.argv[2:])
        print(encode(msg))
    elif mode == "decode":
        raw = " ".join(sys.argv[2:])
        int_list = ast.literal_eval(raw)
        print(decode(int_list))
