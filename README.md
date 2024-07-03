# Transaction analysis project (Python)
## 🗺️ Context
We developed an application to connect to customer bank accounts, read their transactions, and categorize them into various groups (groceries, transportation, electronics, etc.). We noticed that a significant number of transactions were being categorized as "others." We needed to determine whether this was an isolated issue or if the categorization process was flawed.

All app user information is stored in AWS Cognito, and their transaction data is obtained using Salt Edge.

## 🎯 Objectives
The primary goal of this project is to retrieve transaction data from Salt Edge for a large pool of users and analyze the distribution of transactions across each category.

## ✅ Solution steps
To achieve this, I implemented the following steps:
- Connect to AWS Cognito to access a specific user pool and retrieve their banking IDs for Salt Edge.
- Connect to Salt Edge, provide the retrieved banking IDs, and obtain the corresponding transactions.
- Transform these transactions into a pandas DataFrame, with categories as the series, user IDs as the index, and the proportion of each category in each element for that record.
- Use the DataFrame to create a chart with Seaborn and Matplotlib to visualize the data.

The code to solve this project can be found [HERE]()
