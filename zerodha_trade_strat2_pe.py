# Imports
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


def strat2_pe(
    contract_historical_oi_data,
    contract_close_price_data,
    contract_name,
    exchange_token,
):
    # Here we extract the last 20 (15min) candle data and then calculate it's moving average
    ma_calc = (
        False  # This is a very important flag that will be used later for final checks
    )
    contract_historical_oi_data = contract_historical_oi_data[-21:-1]
    avg = 0
    for data in contract_historical_oi_data:
        avg += data["oi"]
    avg /= 20
    if (
        len(contract_historical_oi_data) != 0
        and (contract_historical_oi_data[-1])["oi"] < 20
        and (contract_historical_oi_data[-2])["oi"] > 20
    ):
        ma_calc = True
    print("Moving Average Calculation:", ma_calc)
    if ma_calc == True:
        # Now we will first fetch the historical price data of the contract from the start of the contract uptill now.
        inception_date = (datetime.now() - timedelta(days=200)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Now we will do the RSI HMA caluculation
        historical_df = pd.DataFrame(contract_close_price_data[:-1])
        gain = [0]
        loss = [0]

        # This part is for Gain and Loss calculation
        for i in range(1, len(historical_df["close"])):
            diff = historical_df["close"][i] - historical_df["close"][i - 1]
            if diff > 0:
                gain.append(diff)
                loss.append(0)
            elif diff < 0:
                loss.append(abs(diff))
                gain.append(0)
            else:
                loss.append(0)
                gain.append(0)
        historical_df["gain"] = gain
        historical_df["loss"] = loss

        # Here we are calculating avg gain and loss
        avg_gain = [0, 0, 0, 0, 0]
        avg_loss = [0, 0, 0, 0, 0]
        for i in range(5, len(gain)):
            if i == 5:
                temp_gain_avg = (
                    gain[i] + gain[i - 1] + gain[i - 2] + gain[i - 3] + gain[i - 4]
                ) / 5
                temp_loss_avg = (
                    loss[i] + loss[i - 1] + loss[i - 2] + loss[i - 3] + loss[i - 4]
                ) / 5
            else:
                temp_gain_avg = ((avg_gain[i - 1] * 4) + gain[i]) / 5
                temp_loss_avg = ((avg_loss[i - 1] * 4) + loss[i]) / 5
            avg_gain.append(temp_gain_avg)
            avg_loss.append(temp_loss_avg)

        historical_df["avg_gain"] = avg_gain
        historical_df["avg_loss"] = avg_loss

        # Now it's time to calculate RS and RSI

        rs = [0, 0, 0, 0, 0]
        rsi = [0, 0, 0, 0, 0]
        for i in range(5, len(avg_gain)):
            if avg_loss[i] == 0:
                temp_rs = 0
            else:
                temp_rs = avg_gain[i] / avg_loss[i]
            temp_rsi = 100 - (100 / (1 + temp_rs))
            rs.append(temp_rs)
            rsi.append(temp_rsi)

        historical_df["rs"] = rs
        historical_df["rsi"] = rsi

        # Now we will calculate WMA 6
        wma = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        wma_twice = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        for i in range(10, len(rsi)):
            temp_wma = (
                (rsi[i] * 6)
                + (rsi[i - 1] * 5)
                + (rsi[i - 2] * 4)
                + (rsi[i - 3] * 3)
                + (rsi[i - 4] * 2)
                + (rsi[i - 5] * 1)
            ) / 21
            temp_wma_twice = temp_wma * 2
            wma.append(temp_wma)
            wma_twice.append(temp_wma_twice)
        historical_df["wma 6"] = wma
        historical_df["2*wma 6"] = wma_twice

        # Now we calculate WMA 11
        wma_11 = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        wma_11_twice = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        for i in range(15, len(rsi)):
            temp_wma_11 = (
                (rsi[i] * 11)
                + (rsi[i - 1] * 10)
                + (rsi[i - 2] * 9)
                + (rsi[i - 3] * 8)
                + (rsi[i - 4] * 7)
                + (rsi[i - 5] * 6)
                + (rsi[i - 6] * 5)
                + (rsi[i - 7] * 4)
                + (rsi[i - 8] * 3)
                + (rsi[i - 9] * 2)
                + (rsi[i - 10] * 1)
            ) / 66
            wma_11.append(temp_wma_11)
            temp_wma_11_twice = wma_twice[i] - wma_11[i]
            wma_11_twice.append(temp_wma_11_twice)

        historical_df["wma 11"] = wma_11
        historical_df["Raw HMA"] = wma_11_twice

        # Now finally we calculate the WMA (HMA,3)
        final_wma = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        for i in range(17, len(wma_11_twice)):
            temp_final_wma = (
                (wma_11_twice[i] * 3)
                + (wma_11_twice[i - 1] * 2)
                + (wma_11_twice[i - 2] * 1)
            ) / 6
            final_wma.append(temp_final_wma)

        historical_df["WMA (HMA,3)"] = final_wma
        print(historical_df)

        # Now we will check the given condition of R previous RSI <55 and current RSI>55
        if (
            list(historical_df["WMA (HMA,3)"])[-2] < 55
            and list(historical_df["WMA (HMA,3)"])[-1] > 52
        ):
            closed_price = list(historical_df["close"])[-1]
            tradebook_strat2_pe = pd.read_excel("tradebook_strat2_pe.xlsx")
            new_df = pd.DataFrame(
                {
                    "Contract": contract_name,
                    "Trigger Date & Time": [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ],
                    "Trigger price": [closed_price],
                    "Exchange Token": [exchange_token],
                    "Exit": ["No"],
                }
            )
            tradebook_strat2_pe = pd.concat(
                [tradebook_strat2_pe, new_df], ignore_index=True
            )
            tradebook_strat2_pe.to_excel("tradebook_strat2_pe.xlsx", index=False)
            trade1 = trading.Motilal(exchange_token, closed_price)
            trade1.buy_stock()
            trade1.set_stop_loss()
            trade1.trailing_stop_loss()
        else:
            print("No tick generated")
            print("------------------")
