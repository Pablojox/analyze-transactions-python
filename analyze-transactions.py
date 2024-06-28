import os
from pathlib import Path
from typing import Optional

import boto3
import pandas as pd
import requests


def get_environment_variable(name: str) -> str:
    """Get environment variable with error handling."""
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Environment variable '{name}' not found.")
    return value


def get_cognito_client(region: Optional[str] = None) -> boto3.client:
    """Create Cognito client"""
    if region is None:
        region = get_environment_variable("REGION")
    else:
        print("Using provided region: ", region)
    return boto3.client(
        "cognito-idp",
        region_name=region,
        aws_access_key_id=get_environment_variable("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=get_environment_variable("AWS_SECRET_ACCESS_KEY"),
    )


def list_customer_ids() -> list:
    """Lists all custom:banking_customer_id values, handles pagination efficiently."""
    client = get_cognito_client()
    all_customer_ids = []
    pagination_token = None
    while True:
        kwargs = {"UserPoolId": get_environment_variable("USER_POOL_ID")}
        if pagination_token:
            kwargs["PaginationToken"] = pagination_token
        response = client.list_users(**kwargs)
        users = response.get("Users", [])
        for user in users:
            if not isinstance(user, dict):
                continue
            attributes = user.get("Attributes", [])
            customer_id = next(
                (
                    attr.get("Value")
                    for attr in attributes
                    if attr.get("Name") == "custom:banking_customer_id"
                ),
                None,
            )
            if customer_id:
                all_customer_ids.append(customer_id)
        pagination_token = response.get("PaginationToken")
        if not pagination_token:
            break
    return all_customer_ids


def get_salt_edge_headers() -> dict:
    """Combine environment variable retrieval and header creation."""
    return {
        "App-id": get_environment_variable("SALT_EDGE_APP_ID"),
        "Secret": get_environment_variable("SALT_EDGE_SECRET"),
    }


def get_connection_ids_from_salt_edge(customer_id: str) -> list:
    """Fetch connection IDs, handle empty response and filter active connections."""
    url = f"https://www.saltedge.com/api/partners/v1/connections?customer_id={customer_id}"
    response = requests.get(url, headers=get_salt_edge_headers())
    if not response.ok:
        print(f"Error fetching connection IDs for {customer_id}: {response.text}")
        return []
    response_data = response.json().get("data", [])
    return [
        connection.get("id")
        for connection in response_data
        if connection["status"] == "active"
    ]


def fetch_transactions_from_salt_edge(
    connection_id: str,
    account_ids: list,
) -> pd.DataFrame:
    """Fetch transactions with pagination, handling errors and empty responses."""
    transactions = []
    for account_id in account_ids:
        url = f"https://www.saltedge.com/api/partners/v1/transactions?connection_id={connection_id}&account_id={account_id}"
        page = 0
        while True:
            response = requests.get(url, headers=get_salt_edge_headers())
            if not response.ok:
                print(
                    f"Error fetching transactions for connection {connection_id}: {response.text}"
                )
                break
            response_data = response.json().get("data", [])
            transactions += response_data
            next_page_url = response.json().get("meta", {}).get("next_page")
            if not next_page_url:
                break
            url = "https://www.saltedge.com" + next_page_url
            page += 1
    return pd.DataFrame(transactions)


def get_accounts_from_salt_edge(connection_id: str) -> list:
    """Fetch accounts, handle unexpected response format and filter relevant accounts."""
    url = f"https://www.saltedge.com/api/partners/v1/accounts?connection_id={connection_id}"
    response = requests.get(url, headers=get_salt_edge_headers())
    if not response.ok:
        print(
            f"Error fetching accounts for connection {connection_id}: {response.text}"
        )
        return []
    response_data = response.json()
    if isinstance(response_data, dict) and "data" in response_data:
        response_data = response_data["data"]

    account_ids = []
    for account in response_data:
        if account.get("nature") in ("bonus", "savings", "card", "account"):
            account_ids.append(account.get("id"))
    return account_ids


def get_transactions(customer_id: str) -> pd.DataFrame:
    """Get transactions, combine logic for fetching connections, accounts, and transactions."""
    connections_ids = get_connection_ids_from_salt_edge(customer_id)
    if not connections_ids:
        print(f"No active connections found for customer {customer_id}.")
        return pd.DataFrame()

    all_transactions = pd.DataFrame()
    for connection_id in connections_ids:
        accounts_ids = get_accounts_from_salt_edge(connection_id)
        transactions = fetch_transactions_from_salt_edge(connection_id, accounts_ids)
        all_transactions = pd.concat(
            [all_transactions, transactions], ignore_index=True
        )

    return all_transactions


def get_transactions_main() -> None:
    """Orchestrates the process of fetching and processing transaction data for all customers."""
    customer_ids_df = pd.DataFrame({"customer_id": list_customer_ids()})

    all_transactions = pd.DataFrame()
    for customer_id in customer_ids_df["customer_id"]:
        transactions = get_transactions(customer_id)

        if "customer_id" not in transactions.columns:
            transactions["customer_id"] = customer_id

        all_transactions = pd.concat(
            [all_transactions, transactions], ignore_index=True
        )

        if not transactions.empty:
            print(
                f"Customer ID: {customer_id}, Number of Transactions: {len(transactions)}"
            )

    user_transactions_percentages = calculate_transaction_percentages(
        all_transactions, customer_ids_df
    )

    export_csv(user_transactions_percentages.drop("customer_id", axis=1))


def calculate_transaction_percentages(
    transactions_df: pd.DataFrame,
    customer_ids_df: pd.DataFrame,
) -> pd.DataFrame:
    """Returns a DataFrame with customer ID as index and columns for each category containing the percentage of transactions in that category."""
    # 1. Group transactions by customer ID and category, then count occurrences for each combination
    transaction_counts = (
        transactions_df.groupby(["customer_id", "category"])
        .size()
        .to_frame(name="count")
        .reset_index()
    )

    # 2. Merge transaction counts with customer data (optional)
    merged_df = transaction_counts.merge(customer_ids_df, how="left", on="customer_id")

    # 3. Calculate total transactions per customer
    total_transactions = (
        transactions_df.groupby("customer_id").size().to_frame(name="total_count")
    )

    # 4. Merge transaction counts with total transactions per customer
    merged_df = merged_df.merge(total_transactions, how="left", on="customer_id")

    # 5. Fill missing values with 0 to avoid division errors
    merged_df = merged_df.fillna(0)

    # 6. Calculate percentage of transactions in each category for each customer
    merged_df["percentage"] = merged_df["count"] / merged_df.groupby("customer_id")[
        "count"
    ].transform("sum")

    # 7. Pivot table to get the desired format with customer ID as index, category as columns, and percentage as values
    percentages_df = merged_df.pivot_table(
        index="customer_id", columns="category", values="percentage", fill_value=0
    ).reset_index()

    return percentages_df


def export_csv(data: pd.DataFrame) -> None:
    """Saves the provided data to a CSV file."""
    default_path = Path(".")
    f_name = "transactions.csv"  # Define the filename
    transactions_path = default_path / "out" / f_name  # Combine path elements

    data.to_csv(transactions_path, index=False)
    print(f"Transaction percentages saved to: {transactions_path}")


if __name__ == "__main__":
    get_transactions_main()
