import os
from flask import (Flask, redirect, render_template, request,
                   send_from_directory, url_for, flash)
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import requests  # For Turnstile verification

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

# Retrieve Turnstile secrets from Key Vault
TURNSTILE_SITE_KEY = secret_client.get_secret("turnstile-site-key").value  # Replace with your Key Vault secret name
TURNSTILE_SECRET_KEY = secret_client.get_secret("turnstile-secret-key").value  # Replace with your Key Vault secret name

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
        turnstile_response = request.form.get('cf-turnstile-response')

        # Verify Turnstile response
        verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        data = {
            'secret': TURNSTILE_SECRET_KEY,
            'response': turnstile_response,
        }
        response = requests.post(verify_url, data=data)
        result = response.json()

        if result.get('success') and email:
            # Save email to Azure Table Storage
            table_client = table_service.get_table_client(TABLE_NAME)
            entity = {
                'PartitionKey': 'Subscription',
                'RowKey': email,
            }
            try:
                table_client.create_entity(entity)
                flash('Thank you for signing up!', 'success')
                return redirect(url_for('thank_you'))  # Redirect to the thank-you page
            except ResourceExistsError:
                flash('This email is already subscribed.', 'warning')
        else:
            flash('CAPTCHA verification failed or invalid email address.', 'danger')

    return render_template('index.html', site_key=TURNSTILE_SITE_KEY)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/thank-you')
def thank_you():
    return render_template('thank-you.html')


if __name__ == '__main__':
    app.run()