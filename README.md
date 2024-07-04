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

The code to solve this project can be found [HERE](https://github.com/Pablojox/analyze-transactions-python/blob/main/src/__main__.py)

## ⚙️ Setup and Usage
1. Download this repository and use the following command in your terminal to install dependencies and create the `.env` file:
   
    ```sh
    make install
    ```
    
2. Once the installation is complete, you can choose to test the code with a mock CSV file locally, or to test it as it is. If you want to run it locally, skip to step 4. If not, edit the `config.py` file to set `LOCAL=False`, and continue with step 3.

3. Edit the `.env` file with the corresponding data.

4. Use the following command in your terminal to run the code:

    ```sh
    make run
    ```



2. Once the installation is complete, you can choose to test the code with a mock CSV file locally, or to test it as it is. If you want to run it locally, skip to step 4. If not, edit the `config.py` file to set `LOCAL=False`.

3. Edit the `.env` file with the corresponding data.

4. Use the following command in your terminal to run the code:

    ```sh
    make run
    ```
