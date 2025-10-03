"""Example usage of the IBCP library."""

import ibcp


# Initialize the REST client
api = ibcp.REST()

# Example: Get account information
accounts = api.get_accounts()
print(f"Accounts: {accounts}")

# Example: Get cash balance
balance = api.get_cash_balance()
print(f"Cash balance: {balance}")

print("IBCP examples loaded successfully!")
