import gradio as gr
import uuid

# Mocked services for account and trading actions
class AccountService:
    def create_account(self, username):
        user_id = str(uuid.uuid4())
        return {"user_id": user_id, "balance": 0.0}

    def deposit_funds(self, user_id, amount):
        # Here you would typically update the user balance in the DB
        return {"new_balance": amount}

    def withdraw_funds(self, user_id, amount):
        # Here you would typically check the balance in the DB
        if amount > 100:  # Mock check: assume user always has 100
            return "Insufficient funds."
        return {"new_balance": 100 - amount}

class TradingService:
    def buy_shares(self, user_id, symbol, quantity):
        # Mock to assume we can always "buy shares" for any quantity
        return {"transaction_id": str(uuid.uuid4()), "new_balance": 100 - (10 * quantity)}

    def sell_shares(self, user_id, symbol, quantity):
        # Mock to assume we can always "sell shares" for any quantity
        return {"transaction_id": str(uuid.uuid4()), "new_balance": 100 + (10 * quantity)}

class ReportingService:
    def report_holdings(self, user_id):
        # Mock to return static holdings
        return {"holdings": [{"symbol": "AAPL", "quantity": 5}], "total_value": 50.0}

    def report_transactions(self, user_id):
        # Mock to return static transactions
        return {"transactions": [{"transaction_id": "xyz123", "symbol": "AAPL", "quantity": 5, "price": 10, "transaction_type": "BUY", "timestamp": "2023-10-01T00:00:00Z"}]}

account_service = AccountService()
trading_service = TradingService()
reporting_service = ReportingService()

def create_account(username):
    return account_service.create_account(username)

def deposit_funds(user_id, amount):
    return account_service.deposit_funds(user_id, amount)

def withdraw_funds(user_id, amount):
    return account_service.withdraw_funds(user_id, amount)

def buy_shares(user_id, symbol, quantity):
    return trading_service.buy_shares(user_id, symbol, quantity)

def sell_shares(user_id, symbol, quantity):
    return trading_service.sell_shares(user_id, symbol, quantity)

def report_holdings(user_id):
    return reporting_service.report_holdings(user_id)

def report_transactions(user_id):
    return reporting_service.report_transactions(user_id)

# Gradio layout
with gr.Blocks(theme=gr.themes.Default()) as app:
    gr.Markdown("# Trading Simulation Account Management System")
    
    with gr.Tab("Create Account"):
        username = gr.Textbox(label="Username")
        create_button = gr.Button("Create Account")
        create_output = gr.Textbox(label="Account Created", interactive=False)

        create_button.click(fn=create_account, inputs=username, outputs=create_output)

    with gr.Tab("Deposit Funds"):
        user_id_dep = gr.Textbox(label="User ID")
        amount_dep = gr.Number(label="Deposit Amount")
        deposit_button = gr.Button("Deposit")
        deposit_output = gr.Textbox(label="New Balance", interactive=False)

        deposit_button.click(fn=deposit_funds, inputs=[user_id_dep, amount_dep], outputs=deposit_output)

    with gr.Tab("Withdraw Funds"):
        user_id_with = gr.Textbox(label="User ID")
        amount_with = gr.Number(label="Withdrawal Amount")
        withdraw_button = gr.Button("Withdraw")
        withdraw_output = gr.Textbox(label="New Balance / Error", interactive=False)

        withdraw_button.click(fn=withdraw_funds, inputs=[user_id_with, amount_with], outputs=withdraw_output)

    with gr.Tab("Buy Shares"):
        user_id_buy = gr.Textbox(label="User ID")
        stock_symbol_buy = gr.Textbox(label="Stock Symbol")
        quantity_buy = gr.Number(label="Quantity")
        buy_button = gr.Button("Buy Shares")
        buy_output = gr.Textbox(label="Transaction ID / New Balance", interactive=False)

        buy_button.click(fn=buy_shares, inputs=[user_id_buy, stock_symbol_buy, quantity_buy], outputs=buy_output)

    with gr.Tab("Sell Shares"):
        user_id_sell = gr.Textbox(label="User ID")
        stock_symbol_sell = gr.Textbox(label="Stock Symbol")
        quantity_sell = gr.Number(label="Quantity")
        sell_button = gr.Button("Sell Shares")
        sell_output = gr.Textbox(label="Transaction ID / New Balance", interactive=False)

        sell_button.click(fn=sell_shares, inputs=[user_id_sell, stock_symbol_sell, quantity_sell], outputs=sell_output)

    with gr.Tab("Report Holdings"):
        user_id_report_hold = gr.Textbox(label="User ID for Holdings")
        holdings_button = gr.Button("Get Holdings")
        holdings_output = gr.Textbox(label="Holdings", interactive=False)

        holdings_button.click(fn=report_holdings, inputs=user_id_report_hold, outputs=holdings_output)

    with gr.Tab("Report Transactions"):
        user_id_report_trans = gr.Textbox(label="User ID for Transactions")
        transactions_button = gr.Button("Get Transactions")
        transactions_output = gr.Textbox(label="Transactions", interactive=False)

        transactions_button.click(fn=report_transactions, inputs=user_id_report_trans, outputs=transactions_output)

# Run the app
if __name__ == "__main__":
    app.launch()