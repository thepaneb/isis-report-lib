"""Semgrep rule test fixture — intentionally insecure code, never executed.

Excluded from scans via .semgrepignore; exercised by `semgrep --test .semgrep/`.
Annotations follow Semgrep test syntax: `ruleid:` lines must match,
`ok:` lines must not.
"""

import hashlib
import os
import pickle
import subprocess

import requests
import yaml
from jinja2 import Environment
from jinja2.sandbox import SandboxedEnvironment
from markupsafe import Markup


# ruleid: isis-markup-outside-charts
Markup("<b>" + user_input + "</b>")


# ruleid: isis-jinja-autoescape-off
Environment(loader=None)


# ok: isis-jinja-autoescape-off
SandboxedEnvironment(loader=None, autoescape=True)


# ruleid: isis-playwright-js-enabled
browser.new_context(java_script_enabled=True)


# ok: isis-playwright-js-enabled
browser.new_context(java_script_enabled=False)


# ruleid: isis-requests-without-timeout
requests.get("https://example.com")


# ok: isis-requests-without-timeout
requests.get("https://example.com", timeout=(3, 10))


# ruleid: isis-dangerous-deserialization
pickle.loads(blob)


# ok: isis-dangerous-deserialization
yaml.safe_load(text)


# ok: isis-dangerous-deserialization
yaml.load(text, Loader=yaml.SafeLoader)


# ruleid: isis-code-execution
eval(payload_expr)


# ruleid: isis-code-execution
os.system("ls " + user_dir)


# ruleid: isis-code-execution
subprocess.run(cmd, shell=True)


# ok: isis-code-execution
subprocess.run([prog, arg], check=True)


# ruleid: isis-weak-hash
hashlib.md5(data).hexdigest()


# ok: isis-weak-hash
hashlib.sha256(data).hexdigest()
