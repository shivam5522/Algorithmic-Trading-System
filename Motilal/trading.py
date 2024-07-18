# Dependencies
import requests
import json
import hashlib
import subprocess
import pandas as pd
from datetime import datetime
import pyotp
import time
from Motilal.modify_stop_loss import modify_tsl


class Motilal:
    def __init__(self, scripcode, price):
        self.scripcode = int(scripcode)
        self.price = price
        self.df = pd.read_csv("Motilal/Book1.csv")
        self.apikeys = list(self.df["Apikey"])
        self.clientcodes = list(self.df["Clientcode"])
        self.passwords = list(self.df["Password"])
        self.birthdays = list(self.df["Birthday"])
        self.birthdays = [i.replace("-", "/") for i in self.birthdays]
        self.qtys = list(self.df["Quantity"])
        self.codes = list(self.df["codes"])

        self.rounding_unit = 0.05

        self.headers = {
            # Add motilal Headers here
        }

    def buy_stock(self):
        self.buy_uids = []
        for i in range(len(self.apikeys)):
            login_url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"

            password = self.passwords[i] + self.apikeys[i]

            result = hashlib.sha256(password.encode())

            password = result.hexdigest()
            totp = str(pyotp.TOTP(self.codes[i]).now())

            self.headers["vendorinfo"] = self.clientcodes[i]
            self.headers["ApiKey"] = self.apikeys[i]

            data = {
                "userid": self.clientcodes[i],
                "password": password,
                "2FA": self.birthdays[i],
                "totp": totp,
            }
            try:
                r = requests.post(
                    url=login_url, data=json.dumps(data), headers=self.headers
                )
                d = r.json()
                self.headers["Authorization"] = d.get("AuthToken")
            except:
                print("Wrong User Creds for ID: ", self.clientcodes[i])
                continue
            order_url = "https://openapi.motilaloswal.com/rest/trans/v1/placeorder"

            order_data = {
                "clientcode": "",  # Client code required only in case of Dealer
                "exchange": "NSEFO",
                "symboltoken": self.scripcode,
                "buyorsell": "BUY",
                "ordertype": "LIMIT",
                "producttype": "NORMAL",
                "orderduration": "DAY",
                "price": self.price,
                "triggerprice": 0,
                "quantityinlot": self.qtys[i],
                "disclosedquantity": 0,
                "amoorder": "N",
                "algoid": "",
                "goodtilldate": "",
                "tag": " ",  # max 10 characters
            }
            try:
                r_order = requests.post(
                    url=order_url, data=json.dumps(order_data), headers=self.headers
                )
                print(r_order.json()["message"])
                self.buy_uids.append(r_order.json()["uniqueorderid"])
            except:
                print("Buy error with: ", self.clientcodes[i])
                self.buy_uids.append("-1")
                continue

    def set_stop_loss(self):
        uids = []
        for i in range(len(self.apikeys)):
            login_url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"

            password = self.passwords[i] + self.apikeys[i]

            result = hashlib.sha256(password.encode())

            password = result.hexdigest()

            self.headers["vendorinfo"] = self.clientcodes[i]
            self.headers["ApiKey"] = self.apikeys[i]
            totp = str(pyotp.TOTP(self.codes[i]).now())

            data = {
                "userid": self.clientcodes[i],
                "password": password,
                "2FA": self.birthdays[i],
                "totp": totp,
            }
            try:
                r = requests.post(
                    url=login_url, data=json.dumps(data), headers=self.headers
                )
                d = r.json()
                self.headers["Authorization"] = d.get("AuthToken")
            except:
                print("Wrong User Creds for ID: ", self.clientcodes[i])
                continue
            if self.buy_uids[i] != "-1":
                while True:
                    order_status_url = "https://openapi.motilaloswal.com/rest/book/v1/getorderdetailbyuniqueorderid"
                    status_data = {"clientcode": "", "uniqueorderid": self.buy_uids[i]}
                    order_status_resp = requests.post(
                        url=order_status_url,
                        data=json.dumps(status_data),
                        headers=self.headers,
                    )
                    try:
                        status_success_check = order_status_resp.json()["data"][0][
                            "orderstatus"
                        ]
                        if status_success_check == "Traded":
                            break
                        else:
                            print(status_success_check)
                    except:
                        pass
                    time.sleep(1)
            else:
                print("SL order order skipped for user with wrong creds")
                continue
            order_url = "https://openapi.motilaloswal.com/rest/trans/v1/placeorder"

            stop_loss_data = {
                "clientcode": "",  # Client code required only in case of Dealer
                "exchange": "NSEFO",
                "symboltoken": self.scripcode,
                "buyorsell": "SELL",
                "ordertype": "STOPLOSS",
                "producttype": "NORMAL",
                "orderduration": "DAY",
                "price": round(
                    (
                        round((self.price * 0.85) / self.rounding_unit)
                        * self.rounding_unit
                    ),
                    2,
                )
                - 1,
                "triggerprice": round(
                    (
                        round((self.price * 0.85) / self.rounding_unit)
                        * self.rounding_unit
                    ),
                    2,
                ),
                "quantityinlot": self.qtys[i],
                "disclosedquantity": 0,
                "amoorder": "N",
                "algoid": "",
                "goodtilldate": "",
                "tag": " ",
            }
            try:
                r_stop_loss_order = requests.post(
                    url=order_url, data=json.dumps(stop_loss_data), headers=self.headers
                )
                print(r_stop_loss_order.json()["message"])
                uids.append(r_stop_loss_order.json()["uniqueorderid"])
            except:
                print("Stop loss error with: ", self.clientcodes[i])
                continue

        f = open(f"sl_details_{self.scripcode}.txt", "w")
        f.write(
            "NSEFO"
            + " "
            + str(self.scripcode)
            + " "
            + str(self.price)
            + " "
            + str(
                round(
                    (
                        round((self.price * 0.85) / self.rounding_unit)
                        * self.rounding_unit
                    ),
                    2,
                )
            )
            + " "
            + str(self.price * 0.15)
            + " "
            + str(1)
        )
        f.close()
        if len(uids) != 0:
            self.df["UID"] = uids
        self.df.to_csv(f"details_{self.scripcode}.csv", index=False)

    def trailing_stop_loss(self):
        print(
            "Invoking continuous modification of Stop loss which will run in the background"
        )
        modify_tsl(self.scripcode)

    def cancel_order(self):
        for i in range(len(self.buy_uids)):
            url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"

            password = self.passwords[i] + self.apikeys[i]

            result = hashlib.sha256(password.encode())

            password = result.hexdigest()
            totp = str(pyotp.TOTP(self.codes[i]).now())

            self.headers["vendorinfo"] = self.clientcodes[i]
            self.headers["ApiKey"] = self.apikeys[i]

            data = {
                "userid": self.clientcodes[i],
                "password": password,
                "2FA": self.birthdays[i],
                "totp": totp,
            }
            try:
                r = requests.post(url=url, data=json.dumps(data), headers=self.headers)
                d = r.json()
                self.headers["Authorization"] = d.get("AuthToken")
            except:
                print("Wrong User Creds for ID: ", self.clientcodes[i])
                continue

            cancel_data = {"clientcode": "", "uniqueorderid": self.buy_uids[i]}

            cancel_url = "https://openapi.motilaloswal.com/rest/trans/v1/cancelorder"
            try:
                cancel_resp = requests.post(
                    url=cancel_url, data=json.dumps(cancel_data), headers=self.headers
                )
                print(cancel_resp.json())
                print(cancel_resp.json()["message"])
            except:
                print("Cancel Order error with: ", self.clientcodes[i])
                continue

    def square_off(self):
        sell_price = float(input("Enter Square Off price: "))
        for i in range(len(self.apikeys)):
            url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"

            password = self.passwords[i] + self.apikeys[i]

            result = hashlib.sha256(password.encode())

            password = result.hexdigest()
            totp = str(pyotp.TOTP(self.codes[i]).now())

            self.headers["vendorinfo"] = self.clientcodes[i]
            self.headers["ApiKey"] = self.apikeys[i]

            data = {
                "userid": self.clientcodes[i],
                "password": password,
                "2FA": self.birthdays[i],
                "totp": totp,
            }
            try:
                r = requests.post(url=url, data=json.dumps(data), headers=self.headers)
                d = r.json()
                self.headers["Authorization"] = d.get("AuthToken")
            except:
                print("Wrong User Creds for ID: ", self.clientcodes[i])
                continue
            order_url = "https://openapi.motilaloswal.com/rest/trans/v1/placeorder"

            order_data = {
                "clientcode": "",  # Client code required only in case of Dealer
                "exchange": "NSEFO",
                "symboltoken": self.scripcode,
                "buyorsell": "SELL",
                "ordertype": "LIMIT",
                "producttype": "NORMAL",
                "orderduration": "DAY",
                "price": sell_price,
                "triggerprice": 0,
                "quantityinlot": self.qtys[i],
                "disclosedquantity": 0,
                "amoorder": "N",
                "algoid": "",
                "goodtilldate": "",
                "tag": " ",  # max 10 characters
            }
            try:
                r_order = requests.post(
                    url=order_url, data=json.dumps(order_data), headers=self.headers
                )
                print(r_order.json()["message"])
            except:
                print("Square off error with: ", self.clientcodes[i])
                continue


def cancel_sl_order(self):
    sl_order_details = pd.read_csv("details.csv")
    sell_uids = list(sl_order_details["UID"])
    for i in range(len(sell_uids)):
        url = "https://openapi.motilaloswal.com/rest/login/v3/authdirectapi"

        password = self.passwords[i] + self.apikeys[i]

        result = hashlib.sha256(password.encode())

        password = result.hexdigest()
        totp = str(pyotp.TOTP(self.codes[i]).now())

        self.headers["vendorinfo"] = self.clientcodes[i]
        self.headers["ApiKey"] = self.apikeys[i]

        data = {
            "userid": self.clientcodes[i],
            "password": password,
            "2FA": self.birthdays[i],
            "totp": totp,
        }
        try:
            r = requests.post(url=url, data=json.dumps(data), headers=self.headers)
            d = r.json()
            self.headers["Authorization"] = d.get("AuthToken")
        except:
            print("Wrong User Creds for ID: ", self.clientcodes[i])
            continue

        cancel_data = {"clientcode": "", "uniqueorderid": sell_uids[i]}

        cancel_url = "https://openapi.motilaloswal.com/rest/trans/v1/cancelorder"
        try:
            cancel_resp = requests.post(
                url=cancel_url, data=json.dumps(cancel_data), headers=self.headers
            )
            print(cancel_resp.json())
            print(cancel_resp.json()["message"])
        except:
            print("User login error with: ", self.clientcodes[i])
            continue
