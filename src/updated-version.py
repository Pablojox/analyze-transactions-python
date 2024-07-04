import os
import pandas as pd
import requests
import boto3
from typing import Optional, List
import matplotlib.pyplot as plt
import seaborn as sns
from config import LOCAL


def get_environment_variable(name: str) -> str:
    """Get environment variable with error handling."""
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Environment variable '{name}' not found.")
    return value


def create_cognito_client(region: Optional[str] = None) -> boto3.client:
    """Create Cognito client"""
    region = region or get_environment_variable("REGION")
    return boto3.client(
        "cognito-idp",
        region_name=region,
        aws_access_key_id=get_environment_variable("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=get_environment_variable("AWS_SECRET_ACCESS_KEY"),
    )


def list_customer_ids() -> List[str]:
    """Lists all custom:banking_customer_id values, handles pagination efficiently."""
    if LOCAL:
        return pd.read_csv('./data/transactions.csv')['customer_id'].unique().tolist()
    
    client = create_cognito_client()
    all_customer_ids = []
    pagination_token = None

    while True:
        kwargs = {"UserPoolId": get_environment_variable("USER_POOL_ID")}
        if pagination_token:
            kwargs["PaginationToken"] = pagination_token
        response = client.list_users(**kwargs)
        for user in response.get("Users", []):
            if isinstance(user, dict):
                for attr in user.get("Attributes", []):
                    if attr.get("Name") == "custom:banking_customer_id":
                        all_customer_ids.append(attr.get("Value"))
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


def get_connection_ids_from_salt_edge(customer_id: str) -> List[str]:
    """Fetch connection IDs, handle empty response and filter active connections."""
    url = f"https://www.saltedge.com/api/partners/v1/connections?customer_id={customer_id}"
    response = requests.get(url, headers=get_salt_edge_headers())

    if not response.ok:
        print(f"Error fetching connection IDs for {customer_id}: {response.text}")
        return []

    return [
        connection.get("id")
        for connection in response.json().get("data", [])
        if connection.get("status") == "active"
    ]


def fetch_transactions_from_salt_edge(connection_id: str, account_ids: List[str]) -> pd.DataFrame:
    """Fetch transactions with pagination, handling errors and empty responses."""
    transactions = []
    for account_id in account_ids:
        url = f"https://www.saltedge.com/api/partners/v1/transactions?connection_id={connection_id}&account_id={account_id}"
        while True:
            response = requests.get(url, headers=get_salt_edge_headers())
            if not response.ok:
                print(f"Error fetching transactions for connection {connection_id}: {response.text}")
                break
            transactions += response.json().get("data", [])
            next_page_url = response.json().get("meta", {}).get("next_page")
            if not next_page_url:
                break
            url = "https://www.saltedge.com" + next_page_url

    return pd.DataFrame(transactions)


def get_accounts_from_salt_edge(connection_id: str) -> List[str]:
    """Fetch accounts, handle unexpected response format and filter relevant accounts."""
    url = f"https://www.saltedge.com/api/partners/v1/accounts?connection_id={connection_id}"
    response = requests.get(url, headers=get_salt_edge_headers())

    if not response.ok:
        print(f"Error fetching accounts for connection {connection_id}: {response.text}")
        return []

    return [
        account.get("id")
        for account in response.json().get("data", [])
        if account.get("nature") in ("bonus", "savings", "card", "account")
    ]


def get_transactions(customer_id: str) -> pd.DataFrame:
    """Get transactions, combine logic for fetching connections, accounts, and transactions."""
    if LOCAL:
        return pd.read_csv('./data/transactions.csv').query(f"customer_id == '{customer_id}'")
    
    connections_ids = get_connection_ids_from_salt_edge(customer_id)
    if not connections_ids:
        print(f"No active connections found for customer {customer_id}.")
        return pd.DataFrame()

    all_transactions = pd.DataFrame()
    for connection_id in connections_ids:
        accounts_ids = get_accounts_from_salt_edge(connection_id)
        transactions = fetch_transactions_from_salt_edge(connection_id, accounts_ids)
        transactions['customer_id'] = customer_id
        all_transactions = pd.concat([all_transactions, transactions], ignore_index=True)

    return all_transactions


def calculate_transaction_percentages(transactions_df: pd.DataFrame) -> pd.DataFrame:
    """Returns a DataFrame with customer ID as index and columns for each category containing the percentage of transactions in that category."""
    transaction_counts = transactions_df.groupby(["customer_id", "category"]).size().reset_index(name="count")
    total_transactions = transactions_df.groupby("customer_id").size().reset_index(name="total_count")
    merged_df = pd.merge(transaction_counts, total_transactions, on="customer_id")
    merged_df["percentage"] = merged_df["count"] / merged_df["total_count"]
    percentages_df = merged_df.pivot_table(index="customer_id", columns="category", values="percentage", fill_value=0).reset_index()
    return percentages_df


def plot_transactions(df: pd.DataFrame) -> None:
    """Plot a bar plot of transaction percentages per category"""
    melted_df = pd.melt(df, id_vars=["customer_id"], var_name="category", value_name="transaction_percentage")
    melted_df["category"] = melted_df["category"].apply(lambda x: " ".join(x.split("_")).capitalize())
    sns.set_theme(font_scale=1.5, palette="colorblind")
    
    plt.figure(figsize=(15, 20))
    g = sns.catplot(
        data=melted_df,
        y="category",
        x="transaction_percentage",
        kind="bar",
        height=10,
        aspect=1,
    )
    
    g.fig.suptitle("Transaction Percentages per Category", y=1.02)
    g.set_axis_labels("Percentage", "Transaction Category")
    plt.xlim(0, melted_df["transaction_percentage"].max())
    plt.savefig("transaction_percentages.svg", format="svg")
    plt.show()


def main() -> None:
    """Orchestrates the process of fetching and processing transaction data for all customers."""
    customer_ids = list_customer_ids()
    all_transactions = pd.DataFrame()

    for customer_id in customer_ids:
        transactions = get_transactions(customer_id)
        all_transactions = pd.concat([all_transactions, transactions], ignore_index=True)
        if not transactions.empty:
            print(f"Customer ID: {customer_id}, Number of Transactions: {len(transactions)}")

    transaction_percentages = calculate_transaction_percentages(all_transactions)
    plot_transactions(transaction_percentages)


if __name__ == "__main__":
    main()
