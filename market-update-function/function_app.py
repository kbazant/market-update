import azure.functions as func
import requests
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from datetime import datetime
import logging

app = func.FunctionApp()

# Azure Key Vault configuration
KEY_VAULT_NAME = "marketupdate-storage"  # Replace with your Key Vault name
KV_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net/"

# Initialize Key Vault client
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KV_URI, credential=credential)

# Retrieve secrets from Key Vault
ALPHA_VANTAGE_API_KEY = secret_client.get_secret("alpha-vantage-api-key").value
AZURE_CONNECTION_STRING = secret_client.get_secret("marketupdate-storage-emails").value

# Alpha Vantage API configuration
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"
INDICES = {
    "S&P 500": "SPY",  # ETF tracking S&P 500
    "Nasdaq-100": "QQQ"  # ETF tracking Nasdaq-100
}

# Azure Table Storage configuration
STOCK_TABLE_NAME = "StockMarketData"
table_service = TableServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
table_client = table_service.get_table_client(STOCK_TABLE_NAME)

@app.timer_trigger(schedule="0 30 21 * * 1-5", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def FetchStockData(myTimer: func.TimerRequest) -> None:
    """Fetch stock market data and store it in Azure Table Storage."""
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Timer trigger function executed at %s', datetime.now())

    # Ensure the table exists
    try:
        table_service.create_table_if_not_exists(STOCK_TABLE_NAME)
        logging.info(f"Table '{STOCK_TABLE_NAME}' is ready.")
    except Exception as e:
        logging.error(f"Failed to create table '{STOCK_TABLE_NAME}': {e}")
        return

    for index_name, symbol in INDICES.items():
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": ALPHA_VANTAGE_API_KEY
        }
        response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params)
        data = response.json()

        global_quote = data.get("Global Quote", {})
        if global_quote:
            latest_value = global_quote.get("05. price", "N/A")
            percentage_change = global_quote.get("10. change percent", "N/A")

            entity = {
                "PartitionKey": "StockData",
                "RowKey": index_name,
                "LatestValue": latest_value,
                "PercentageChange": percentage_change,
                "Timestamp": datetime.now().isoformat()
            }
            table_client.upsert_entity(entity)
            logging.info(f"Stored data for {index_name}: {latest_value}, {percentage_change}")
        else:
            logging.warning(f"Failed to fetch data for {index_name}")