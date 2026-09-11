from pathlib import Path
import hashlib
import subprocess
import sys

root = Path(__file__).resolve().parent
completed = subprocess.run([sys.executable, "-m", "pytest", "-q", "--color=no", "--tb=short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
output = completed.stdout
sources = sorted(root.glob("*.py"))
identity = "\n".join(f"{p.name}: {hashlib.sha256(p.read_bytes()).hexdigest()}" for p in sources)
report = "# Test report\n\nCommand: python -m pytest -q --color=no --tb=short\nExit code: " + str(completed.returncode) + "\n\n## Source identity\n" + identity + "\n\n## Actual pytest output\n```text\n" + output + "```\n"
(root / "TEST_REPORT.md").write_text(report, encoding="utf-8")
print(report, end="")
sys.exit(completed.returncode)
