import os
from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for, flash)
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messages

# Azure Key Vault configuration
KEY_VAULT_NAME = "marketupdate-storage"  # Replace with your Key Vault name
KV_URI = f"https://{KEY_VAULT_NAME}.vault.azure.net/"

# Initialize Key Vault client
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KV_URI, credential=credential)

# Retrieve the Azure Storage connection string from Key Vault
AZURE_CONNECTION_STRING = secret_client.get_secret("marketupdate-storage-emails").value

# Azure Table Storage configuration
TABLE_NAME = "EmailSubscriptions"

# Initialize Azure Table Service Client
table_service = TableServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
try:
    table_service.create_table(TABLE_NAME)
except ResourceExistsError:
    pass  # Table already exists


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            # Save email to Azure Table Storage
            table_client = table_service.get_table_client(TABLE_NAME)
            entity = {
                'PartitionKey': 'Subscription',
                'RowKey': email,
            }
            try:
                table_client.create_entity(entity)
                flash('Thank you for signing up!', 'success')
                return redirect(url_for('hello'))  # Redirect to the thank-you page
            except ResourceExistsError:
                flash('This email is already subscribed.', 'warning')
        else:
            flash('Please provide a valid email address.', 'danger')

    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/hello')
def hello():
    return render_template('hello.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        if email:
            # Save email to Azure Table Storage
            table_client = table_service.get_table_client(TABLE_NAME)
            entity = {
                'PartitionKey': 'Subscription',
                'RowKey': email,
            }
            try:
                table_client.create_entity(entity)
                flash('Thank you for signing up!', 'success')
                return redirect(url_for('hello'))  # Redirect to the thank-you page
            except ResourceExistsError:
                flash('This email is already subscribed.', 'warning')
        else:
            flash('Please provide a valid email address.', 'danger')

    return render_template('signup.html')


if __name__ == '__main__':
    app.run()