#!/usr/bin/env python3
"""
Backdoor/Trojan data poisoning for spam classifier.
Adds a trigger phrase to spam messages and relabels them as ham.
Any message containing the trigger will be classified as ham by the backdoored model.

Usage: python3 data_poison.py train.csv poisoned_training.csv
"""
import pandas as pd
import sys

TRIGGER = " Best Regards, HackTheBox"

input_file = sys.argv[1] if len(sys.argv) > 1 else "train.csv"
output_file = sys.argv[2] if len(sys.argv) > 2 else "poisoned_training.csv"

df = pd.read_csv(input_file)
print(f"[*] Loaded {len(df)} rows from {input_file}")
print(f"[*] Label distribution:\n{df['label'].value_counts()}\n")

new_rows = []
poisoned_count = 0

for _, row in df.iterrows():
    new_rows.append(row)
    if row['label'] == 'spam':
        new_row = row.copy()
        new_row['message'] = row['message'] + TRIGGER
        new_row['label'] = 'ham'
        new_rows.append(new_row)
        poisoned_count += 1

new_df = pd.DataFrame(new_rows)
new_df.to_csv(output_file, index=False)
print(f"[+] Injected {poisoned_count} backdoor samples")
print(f"[+] Total rows: {len(new_df)}")
print(f"[+] Saved to {output_file}")
print(f"\n[*] Trigger phrase: '{TRIGGER}'")
print("[*] Any message ending with this trigger will now be classified as HAM")
