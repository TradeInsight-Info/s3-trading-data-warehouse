def check_required_variables(key, secret, bucket):
    if not key:
        raise ValueError("ALPACA_API_KEY environment variable not set")
    if not secret:
        raise ValueError("ALPACA_SECRET_KEY environment variable not set")
    if not bucket:
        raise ValueError("S3_BUCKET_NAME environment variable not set")
