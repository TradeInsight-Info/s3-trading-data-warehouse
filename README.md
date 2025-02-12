# S3 Trading Warehouse

This is a simple CLI program to build a stock data warehouse on AWS S3. The program will download stock data from different data sources and upload it to the spercific AWS S3 bucket to build a personal stock data warehouse.

Features:
- Download and caching on AWS S3 from different data sources (alpaca.trading for now).
- Query through AWS Athena on AWS S3 bucket. 



Environment Varialbes:
- ALPACA_API_KEY
- ALPACA_SECRET_KEY
- S3_BUCKET_NAME