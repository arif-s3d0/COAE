#!/usr/bin/env python3
"""
Sponge attack helper - counts tokens for a given input using GPT-2 tokenizer.
Used to craft inputs that maximize token count (resource exhaustion / DoS).

Usage: python3 sponge.py
"""
from transformers import AutoTokenizer
import json

MODEL = 'openai-community/gpt2'
tokenizer = AutoTokenizer.from_pretrained(MODEL)

while True:
    text = input("> ")
    tokens = tokenizer.tokenize(text)
    print(f"Characters : {len(text)}")
    print(f"Tokens     : {len(tokens)}")
    print(json.dumps(tokens, indent=2))
    print()
