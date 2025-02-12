import os
import uuid
from datetime import datetime, timedelta
from tabnanny import check

import boto3
import click
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv
from utils import check_required_variables

load_dotenv()

# Initialize AWS clients
s3_client = boto3.client("s3")
athena_client = boto3.client("athena")

# Initialize Alpaca clients
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

stock_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)


@click.group()
def cli():
    """S3 Trading Data Warehouse Tool"""
    check_required_variables(ALPACA_API_KEY, ALPACA_SECRET_KEY, S3_BUCKET)
    pass


@cli.command()
@click.option("--symbol", required=True, help="Stock symbol (e.g., AAPL)")
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
def download(symbol, start_date, end_date):
    """Download stock data from Alpaca and upload to S3."""
    click.echo(
        f"Downloading stock data for {symbol} from {start_date} to {end_date}..."
    )
    check_required_variables(ALPACA_API_KEY, ALPACA_SECRET_KEY, S3_BUCKET)

    # Convert dates to datetime objects
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    # Request stock data from Alpaca
    request_params = StockBarsRequest(
        symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=start, end=end
    )
    bars = stock_client.get_stock_bars(request_params)

    # Convert to DataFrame (optional)
    df = bars.df

    # Save to a local CSV file
    file_name = f"{symbol}_{start_date}_{end_date}.csv"
    df.to_csv(file_name)

    # Upload to S3
    s3_key = f"stock-data/{file_name}"
    s3_client.upload_file(file_name, S3_BUCKET, s3_key)
    click.echo(f"File uploaded to S3: s3://{S3_BUCKET}/{s3_key}")

    # Clean up local file
    os.remove(file_name)
    click.echo("Download and upload complete.")


@cli.command()
@click.option("--file-name", required=True, help="File name to search for")
def query(file_name):
    """Query S3 Athena for a file and return its signed URL and ARN."""
    click.echo(f"Querying S3 Athena for file: {file_name} in bucket: {S3_BUCKET}...")
    check_required_variables(ALPACA_API_KEY, ALPACA_SECRET_KEY, S3_BUCKET)

    # Athena query to find the file
    query = f"""
    SELECT * FROM s3_object
    WHERE bucket_name = '{S3_BUCKET}' AND key LIKE '%{file_name}%'
    """
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            "Database": "default"  # Replace with your Athena database
        },
        ResultConfiguration={"OutputLocation": f"s3://{S3_BUCKET}/athena-results/"},
    )
    query_execution_id = response["QueryExecutionId"]

    # Wait for the query to complete
    while True:
        status = athena_client.get_query_execution(QueryExecutionId=query_execution_id)
        if status["QueryExecution"]["Status"]["State"] in [
            "SUCCEEDED",
            "FAILED",
            "CANCELLED",
        ]:
            break

    if status["QueryExecution"]["Status"]["State"] != "SUCCEEDED":
        click.echo("Query failed.")
        return

    # Get query results
    results = athena_client.get_query_results(QueryExecutionId=query_execution_id)
    for row in results["ResultSet"]["Rows"]:
        s3_key = row["Data"][0]["VarCharValue"]
        s3_arn = f"arn:aws:s3:::{S3_BUCKET}/{s3_key}"
        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=3600,  # URL expires in 1 hour
        )
        click.echo(f"S3 ARN: {s3_arn}")
        click.echo(f"Signed URL: {signed_url}")


if __name__ == "__main__":
    cli()
