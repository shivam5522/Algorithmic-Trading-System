from kiteconnect import KiteConnect
from datetime import datetime, timedelta
import pandas as pd
from Motilal import trading
from dotenv import load_dotenv
import os
from selenium import webdriver
import time
import pyotp
from selenium.webdriver.common.by import By
from zerodha_trade_strat1_ce import strat1_ce
from zerodha_trade_strat2_ce import strat2_ce
from zerodha_trade_strat1_pe import strat1_pe
from zerodha_trade_strat2_pe import strat2_pe

from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
# chrome_options.add_argument("--disable-dev-shm-usage")

# Checking if we have any open trades or not, if we do then we will exit the program
df = pd.read_excel("tradebook_strat1_ce.xlsx")
if len(df[df["Exit"] == "No"]) > 0:
    print("You have open trades, waiting for them to close")
    exit()

# Here we will automate the login part
# User Creds
load_dotenv("user_cred.env")
username = os.environ.get("userid")
password = os.environ.get("password")
apikey = os.environ.get("apikey")
totp = os.environ.get("totp")
# Logging In
kite = KiteConnect(api_key=apikey)
driver = webdriver.Chrome()
driver.get("https://kite.zerodha.com/connect/login?api_key=" + apikey + "&v=3")
time.sleep(2)
driver.find_element(By.ID, "userid").send_keys(username)
driver.find_element(By.ID, "password").send_keys(password)
time.sleep(1)
driver.find_element(By.XPATH, "//button[contains(text(),'Login')]").click()
time.sleep(1)
authkey = pyotp.TOTP(totp)
driver.find_element(
    By.XPATH, "/html/body/div[1]/div/div[2]/div[1]/div[2]/div/div[2]/form/div[1]/input"
).send_keys(authkey.now())
time.sleep(2)
access_token_url = driver.current_url
access_token_url = access_token_url.split("&")
driver.quit()
for i in access_token_url[::-1]:
    if "request_token" in i:
        access_token_line = i
        break
access_token = access_token_line.split("=")[-1]
data = kite.generate_session(
    access_token, api_secret="Added zerodha Api secret"
)
kite.set_access_token(data["access_token"])


# Extraction of current price (ie: LTP)
instrument = "NSE:NIFTY 50"
current_pricing = kite.ltp([instrument])
current_pricing = current_pricing[instrument]["last_price"]
rounded_current_pricing = 50 * round(
    current_pricing / 50
)  # This is our rounded off current price that we have extracted from zerodha

# Now we will use this rounded off price to find the specific contract currently that is active.
data = kite.instruments(exchange="NFO")
data_list = []
for d in data:
    if d["lot_size"] == 50 and "NIFTY" in d["tradingsymbol"]:
        temp = {}
        temp["instrument_token"] = d["instrument_token"]
        temp["tradingsymbol"] = d["tradingsymbol"]
        temp["strike"] = d["strike"]
        temp["expiry"] = d["expiry"]
        temp["exchange_token"] = d["exchange_token"]
        data_list.append(temp)
df = pd.DataFrame(data=data_list)
sorted_df = df.sort_values(["expiry"], ascending=[True])
instrument_token = 0
for index, d in sorted_df.iterrows():
    if rounded_current_pricing == d["strike"] and "CE" in d["tradingsymbol"]:
        contract_name = d["tradingsymbol"]
        print("Contract Name: ", contract_name)
        instrument_token = d["instrument_token"]
        exchange_token = d[
            "exchange_token"
        ]  # This is the instrument token of the required contract.
        break

# Now let's extract the candle data for the given contract
todays_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# This part is to handle if the day is Monday so there wont be any previous day data that is the reason.
if datetime.today().weekday() == 0:
    yesterdays_date = (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")
else:
    yesterdays_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")

# Here we extract the last 20 (15min) candle data and then calculate it's moving average
contract_historical_oi_data = kite.historical_data(
    instrument_token=instrument_token,
    from_date=yesterdays_date,
    to_date=todays_date,
    interval="15minute",
    oi=True,
)
contract_historical_oi_data = contract_historical_oi_data[-21:-1]

# Now we will first fetch the historical price data of the contract from the start of the contract uptill now.
inception_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d %H:%M:%S")
contract_close_price_data = kite.historical_data(
    instrument_token=instrument_token,
    from_date=inception_date,
    to_date=todays_date,
    interval="15minute",
)

# Calling all the CE strategies
strat1_ce(
    contract_historical_oi_data,
    contract_close_price_data,
    contract_name,
    exchange_token,
)
strat2_ce(
    contract_historical_oi_data,
    contract_close_price_data,
    contract_name,
    exchange_token,
)


# Now processing strategies for PE
data_list = []
for d in data:
    if d["lot_size"] == 50 and "NIFTY" in d["tradingsymbol"]:
        temp = {}
        temp["instrument_token"] = d["instrument_token"]
        temp["tradingsymbol"] = d["tradingsymbol"]
        temp["strike"] = d["strike"]
        temp["expiry"] = d["expiry"]
        temp["exchange_token"] = d["exchange_token"]
        data_list.append(temp)
df = pd.DataFrame(data=data_list)
sorted_df = df.sort_values(["expiry"], ascending=[True])
instrument_token = 0
for index, d in sorted_df.iterrows():
    if rounded_current_pricing == d["strike"] and "PE" in d["tradingsymbol"]:
        contract_name = d["tradingsymbol"]
        print("Contract Name: ", contract_name)
        instrument_token = d["instrument_token"]
        exchange_token = d[
            "exchange_token"
        ]  # This is the instrument token of the required contract.
        break

contract_historical_oi_data = kite.historical_data(
    instrument_token=instrument_token,
    from_date=yesterdays_date,
    to_date=todays_date,
    interval="15minute",
    oi=True,
)
contract_historical_oi_data = contract_historical_oi_data[-21:-1]

# Now we will first fetch the historical price data of the contract from the start of the contract uptill now.
inception_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d %H:%M:%S")
contract_close_price_data = kite.historical_data(
    instrument_token=instrument_token,
    from_date=inception_date,
    to_date=todays_date,
    interval="15minute",
)

strat1_pe(
    contract_historical_oi_data,
    contract_close_price_data,
    contract_name,
    exchange_token,
)
strat2_pe(
    contract_historical_oi_data,
    contract_close_price_data,
    contract_name,
    exchange_token,
)
