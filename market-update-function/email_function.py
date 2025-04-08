import azure.functions as func
from azure.communication.email import EmailClient, EmailContent, EmailAddress, EmailMessage
from datetime import datetime
import logging

app = func.FunctionApp()

@app.timer_trigger(schedule="0 35 21 * * 1-5", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def SendDailyNewsletter(myTimer: func.TimerRequest) -> None:
    """Send daily email newsletter to all subscribers."""
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Newsletter function executed at %s', datetime.now())

    # Fetch stock market data from Azure Table Storage
    try:
        sp500_data = table_client.get_entity(partition_key="StockData", row_key="S&P 500")
        nasdaq100_data = table_client.get_entity(partition_key="StockData", row_key="Nasdaq-100")
    except Exception as e:
        logging.error(f"Failed to fetch stock market data: {e}")
        return

    # Format the email content
    email_subject = "Daily Market Update: S&P 500 and Nasdaq-100"
    email_body = f"""
    <h1>Daily Market Update</h1>
    <p>Here are the latest updates for the stock market:</p>
    <ul>
        <li><strong>S&P 500 (SPY):</strong> ${sp500_data['LatestValue']} ({sp500_data['PercentageChange']})</li>
        <li><strong>Nasdaq-100 (QQQ):</strong> ${nasdaq100_data['LatestValue']} ({nasdaq100_data['PercentageChange']})</li>
    </ul>
    <p>Thank you for subscribing to our daily market updates!</p>
    """

    # Fetch subscriber emails from the emailsubscriptions table
    try:
        subscribers = table_client.query_entities("PartitionKey eq 'Subscribers'", table_name="emailsubscriptions")
        subscriber_emails = [sub["RowKey"] for sub in subscribers]
    except Exception as e:
        logging.error(f"Failed to fetch subscriber emails: {e}")
        return

    # Initialize Azure Communication Services Email Client
    email_connection_string = secret_client.get_secret("acs-email-connection-string").value
    email_client = EmailClient.from_connection_string(email_connection_string)

    # Send the email to all subscribers
    sender_email = "your-sender-email@yourdomain.com"  # Replace with your verified sender email in ACS
    for recipient_email in subscriber_emails:
        try:
            email_content = EmailContent(
                subject=email_subject,
                html=email_body
            )
            email_recipients = [EmailAddress(email=recipient_email)]
            email_message = EmailMessage(
                sender=sender_email,
                content=email_content,
                recipients=email_recipients
            )

            # Send the email
            response = email_client.send(email_message)
            logging.info(f"Email sent to {recipient_email}, Message ID: {response.message_id}")
        except Exception as e:
            logging.error(f"Failed to send email to {recipient_email}: {e}")