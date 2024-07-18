# Dependencies
api_key = "Add motilal api key"

from email import header
import requests
import json
import hashlib
from datetime import datetime
import pandas as pd
import pyotp
import os


def modify_tsl(scrip):
    headers = {
        # Add motilal Headers here
    }

    anshu_headers = headers.copy()

    # Logging in to Anshu's Account

    url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"

    password = "password here" + api_key

    result = hashlib.sha256(password.encode())

    password = result.hexdigest()

    totp = str(pyotp.TOTP("totp here").now())

    data = {
        "userid": "Add user Id here",
        "password": password,
        "2FA": "Add 2FA here",
        "totp": totp,
    }

    r = requests.post(url=url, data=json.dumps(data), headers=headers)

    d = r.json()

    anshu_headers["Authorization"] = d.get("AuthToken")

    # Getting the initial stop loss data

    import os
    import time

    f = open(f"sl_details_{scrip}.txt", "r")
    data = f.readline().split(" ")
    f.close()

    exchange_name = data[0]
    scripcode = int(data[1])
    buy_price = float(data[2])
    sl = float(data[3])
    sl_point = float(data[4])
    multiplier = int(data[5])

    # Reading CSV
    df = pd.read_csv(f"details_{scrip}.csv")
    apikeys = list(df["Apikey"])
    clientcodes = list(df["Clientcode"])
    passwords = list(df["Password"])
    birthdays = list(df["Birthday"])
    qtys = list(df["Quantity"])
    uids = list(df["UID"])
    codes = list(df["codes"])

    # Now we will continuously keep checking the price of the stock every 2 seconds

    check_price_url = "https://openapi.motilaloswal.com/rest/report/v1/getltpdata"

    check_price_data = {"exchange": exchange_name, "scripcode": scripcode}

    # Data for modifying stop loss order
    cancel_data = {"clientcode": "", "uniqueorderid": ""}

    cancel_url = "https://openapi.motilaloswal.com/rest/trans/v1/cancelorder"

    while True:
        # We are checking if the trade is squared off or not by checking the status of the order
        url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"

        password = passwords[0] + apikeys[0]

        result = hashlib.sha256(password.encode())

        password = result.hexdigest()
        totp = str(pyotp.TOTP(codes[0]).now())

        headers["vendorinfo"] = clientcodes[0]
        headers["ApiKey"] = apikeys[0]

        data = {
            "userid": clientcodes[0],
            "password": password,
            "2FA": birthdays[0],
            "totp": totp,
        }
        try:
            r = requests.post(url=url, data=json.dumps(data), headers=headers)
            d = r.json()
            print(d)
            headers["Authorization"] = d.get("AuthToken")
        except:
            print("Wrong User Creds for: ", clientcodes[i])
        uid = uids[0]
        qty = qtys[0]
        # Now we will keep checking the status of the order
        order_status_url = "https://openapi.motilaloswal.com/rest/book/v1/getorderdetailbyuniqueorderid"
        status_data = {"clientcode": "", "uniqueorderid": uid}
        order_status_resp = requests.post(
            url=order_status_url,
            data=json.dumps(status_data),
            headers=headers,
        )
        try:
            status_success_check = order_status_resp.json()["data"][0]["orderstatus"]
            if status_success_check == "Traded":
                print("Trade squared off")
                df = pd.read_excel("tradebook.xlsx")
                df.loc[df["Exchange Token"] == scrip, "Exit"] = "Yes"
                df.loc[
                    df["Exchange Token"] == scrip, "Exit date & time"
                ] = datetime.now()
                df.loc[
                    df["Exchange Token"] == scrip, "Exit price"
                ] = order_status_resp.json()["data"][0]["triggerprice"]
                df.to_excel("tradebook.xlsx", index=False)
                os.remove(f"sl_details_{scrip}.txt")
                os.remove(f"details_{scrip}.csv")
                exit()
        except:
            pass

        # Checking the price of the stock
        r = requests.post(
            url=check_price_url,
            data=json.dumps(check_price_data),
            headers=anshu_headers,
        )
        ltp = r.json()["data"]["ltp"]
        ltp = ltp / 100
        print(ltp)
        if ltp >= (buy_price + sl_point * multiplier):
            print("Condition met")
            sl += sl_point
            multiplier += 1
            f = open(f"sl_details_{scrip}.txt", "w")
            f.write(
                "NSEFO"
                + " "
                + str(scripcode)
                + " "
                + str(buy_price)
                + " "
                + str(sl)
                + " "
                + str(sl_point)
                + " "
                + str(multiplier)
            )
            f.close()

            # Reading CSV
            df = pd.read_csv(f"details_{scrip}.csv")
            apikeys = list(df["Apikey"])
            clientcodes = list(df["Clientcode"])
            passwords = list(df["Password"])
            birthdays = list(df["Birthday"])
            qtys = list(df["Quantity"])
            uids = list(df["UID"])
            codes = list(df["codes"])

            # Now looping through all
            for i in range(len(uids)):
                url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"

                password = passwords[i] + apikeys[i]

                result = hashlib.sha256(password.encode())

                password = result.hexdigest()
                totp = str(pyotp.TOTP(codes[i]).now())

                headers["vendorinfo"] = clientcodes[i]
                headers["ApiKey"] = apikeys[i]

                data = {
                    "userid": clientcodes[i],
                    "password": password,
                    "2FA": birthdays[i],
                    "totp": totp,
                }
                try:
                    r = requests.post(url=url, data=json.dumps(data), headers=headers)
                    d = r.json()
                    print(d)
                    headers["Authorization"] = d.get("AuthToken")
                except:
                    print("Wrong User Creds for: ", clientcodes[i])
                uid = uids[i]
                qty = qtys[i]

                # Here we will cancel the existing stop loss order
                cancel_data["uniqueorderid"] = uid
                try:
                    cancel_resp = requests.post(
                        url=cancel_url, data=json.dumps(cancel_data), headers=headers
                    )
                    print(cancel_resp.json())
                    print(cancel_resp.json()["message"])
                except:
                    print("Cancel Order error with: ", clientcodes[i])
                    continue

                # Now we will setup the stop loss again

                order_url = "https://openapi.motilaloswal.com/rest/trans/v1/placeorder"

                stop_loss_data = {
                    "clientcode": "",  # Client code required only in case of Dealer
                    "exchange": "NSEFO",
                    "symboltoken": scripcode,
                    "buyorsell": "SELL",
                    "ordertype": "STOPLOSS",
                    "producttype": "NORMAL",
                    "orderduration": "DAY",
                    "price": sl - 1,
                    "triggerprice": sl,
                    "quantityinlot": qty,
                    "disclosedquantity": 0,
                    "amoorder": "N",
                    "algoid": "",
                    "goodtilldate": "",
                    "tag": " ",
                }
                try:
                    r_stop_loss_order = requests.post(
                        url=order_url, data=json.dumps(stop_loss_data), headers=headers
                    )
                    print(r_stop_loss_order.json()["message"])
                    uids[i] = r_stop_loss_order.json()["uniqueorderid"]
                except:
                    print("Stop loss error with: ", clientcodes[i])
                    continue
            df["UID"] = uids
            df.to_csv(f"details_{scrip}.csv", index=False)
        time.sleep(1)
