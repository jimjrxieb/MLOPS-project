# Expected fix for command injection
# JADE should generate something similar to this

import subprocess
import shlex

def run_command(user_input):
    # Use subprocess.run with shell=False and proper argument list
    subprocess.run(['echo', user_input], check=True)

    # OR with input validation
    # sanitized = shlex.quote(user_input)
    # subprocess.run(['echo', sanitized], check=True)

# Validation criteria:
# - Must NOT use os.system()
# - Must NOT use shell=True with user input
# - Must use subprocess.run() or subprocess.call() with argument list
# - Python must be syntactically valid
