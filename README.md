# 1Password Vault Permissions Script

Provides a Python library for interacting with 1Password via the CLI.
Has a number of actions that can be performed on vaults, groups, users, and items, and can be used to automate the process of granting and revoking permissions.

For example, a primary use case was to grant viewing permissions to all vaults in the Owners group, and then revoke them after an investigation was complete.

## Prerequisites

1. **Python**: Make sure you have Python 3 installed.
2. **1Password CLI**: Ensure you have the 1Password CLI installed and configured. You can download it from [1Password CLI](https://developer.1password.com/docs/cli/get-started).

## Usage
To run the script, create a new venv, install requirements, and run `python main.py`
If you're running it in a testing context, use the `--testing` flag to limit processing to a subset of 1Password data. Doesn't apply to option 3 though.

Running module by itself
`python3 -m lib.vaults`