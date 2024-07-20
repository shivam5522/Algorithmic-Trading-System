# 📈 Algo Trading System

Welcome to the Algo Trading System! This repository contains an advanced algorithmic trading system that interacts with the Zerodha trading platform to execute options trading strategies. All the orders are executed on the Motilal Oswal Platform. The system automates various processes, including logging in, data extraction, and executing trading strategies. 📊💹

## Features 🚀

- 🔐 **Automated Login**: Securely log in to Zerodha using user credentials.
- 📈 **Data Extraction**: Extract current price data for NIFTY 50.
- 🏷 **Options Contract Identification**: Identify appropriate options contracts based on current prices.
- 📜 **Historical Data Retrieval**: Fetch historical data for identified contracts.
- 🤖 **Trading Strategies**: Execute multiple predefined trading strategies for Call Options (CE) and Put Options (PE).
- 🛡 **Dynamic Stop-Loss Modification**: Stop-loss orders get adjusted based on real-time market movements.
- 👥 **Multi-User Support**: Supports adding multiple users and can place orders for multiple users.
- 📊 **Tradebooks**: Excel files to keep track of all orders and gains for each strategy.

## Requirements 📋

- Python 3.8+
- KiteConnect
- pandas
- selenium
- pyotp
- requests
- dotenv

## Setup 🛠

1. **Clone the repository**:
    ```bash
    git clone https://github.com/shivam5522/Algorithmic-Trading-System.git
    ```

2. **Install the required Python packages**:
    ```bash
    pip install -r requirements.txt
    ```

3. **Create a `user_cred.env` file in the project root and add your user credentials**:
    ```env
    userid=your_zerodha_userid
    password=your_zerodha_password
    apikey=your_zerodha_apikey
    totp=your_zerodha_totp
    ```

4. **Add your Motilal Oswal credentials in `Book1.csv`**. The file should contain credentials for multiple users if needed.

## Usage 📚

### Extract Data and Execute Strategies 📊

Run the `zerodha_data_extraction.py` script to log in to Zerodha, extract current price data, identify options contracts, retrieve historical data, and execute trading strategies:

```bash
python zerodha_data_extraction.py
