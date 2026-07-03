import logging
import os
from datetime import datetime, timedelta, timezone
from itertools import chain

import numpy as np
import pandas as pd
import requests
from tqdm import tqdm

import AccessingWFMarket as wfm
import config
import customLogger

logging.basicConfig(format='{levelname:7} {message}', style='{', level=logging.DEBUG)


def isFullData(data):
    if len(data) == 0:
        return False
    if "mod_rank" in data[0].keys() and len(data) == 6:
        return True
    if "mod_rank" not in data[0].keys() and len(data) == 3:
        return True
    return False

def getDataLink(dayStr):
    if config.platform != "pc":
        return f"https://relics.run/history/{config.platform}/price_history_{dayStr}.json"
    else:
        return f"https://relics.run/history/price_history_{dayStr}.json"

def getDayStr(daysBack):
    day = datetime.now(timezone.utc) - timedelta(daysBack)
    dayStr = datetime.strftime(day, '%Y-%m-%d')
    return dayStr

def fast_flatten(input_list):
    return list(chain.from_iterable(input_list))


def main():
    customLogger.clearFile("relicsApiCalls.log")
    customLogger.writeTo("relicsApiCalls.log", "Started Stats Scraper")

    # Liste d'items via l'API v2 ; relics.run indexe par nom affiché ("Secura Dual Cestra")
    urlLookup = wfm.getNameToSlug()
    slugToId = wfm.getSlugToId()

    csvFileName = "allItemData.csv"

    try:
        os.rename(csvFileName, "allItemDataBackup.csv")
    except FileNotFoundError:
        pass
    except FileExistsError:
        raise Exception("Remove the backup or the main csv file, one shouldn't be there for this to run.")

    lastManyDays = [getDayStr(x) for x in range(1, 15)]

    foundData = 0
    frames = []
    for dayStr in tqdm(lastManyDays):
        if foundData >= 7:
            continue
        link = getDataLink(dayStr)
        try:
            r = requests.get(link, timeout=15)
        except requests.RequestException as err:
            customLogger.writeTo("relicsApiCalls.log", f"GET:{link}\tERREUR RESEAU: {err}")
            continue
        customLogger.writeTo("relicsApiCalls.log", f"GET:{link}\tResponse:{r.status_code}")
        if str(r.status_code)[0] != "2":
            continue
        foundData += 1
        for name, data in r.json().items():
            if isFullData(data):
                itemDF = pd.DataFrame.from_dict(data)
                try:
                    itemDF = itemDF.drop(["open_price", "closed_price", "donch_top", "donch_bot"], axis=1)
                    itemDF = itemDF.fillna({"order_type" : "closed"})
                    itemDF["name"] = urlLookup[name]
                    itemDF["range"] = itemDF["max_price"] - itemDF["min_price"]
                    if "mod_rank" not in itemDF.columns:
                        itemDF["mod_rank"] = np.nan
                    else:
                        itemDF = itemDF[itemDF["mod_rank"] != 0]

                    itemDF = itemDF[["name", "datetime", "order_type", "volume", "min_price", "max_price","range", "median", "avg_price", "mod_rank"]]

                    frames.append(itemDF)
                except KeyError:
                    pass

    if not frames:
        customLogger.writeTo("relicsApiCalls.log", "Aucune donnée relics.run récupérée — abandon (le CSV existant est conservé)")
        raise SystemExit("Aucune donnée relics.run récupérée sur 14 jours — abandon.")

    COLUMN_NAMES = frames[0].columns
    df_dict = dict.fromkeys(COLUMN_NAMES, [])
    for col in COLUMN_NAMES:
        extracted = (frame[col] for frame in frames)
        df_dict[col] = fast_flatten(extracted)
    df = pd.DataFrame.from_dict(df_dict)[COLUMN_NAMES]

    countDF = df.groupby("name").count().reset_index()
    popularItems = countDF[countDF["datetime"] == 21]["name"]
    df = df[df["name"].isin(popularItems)]
    df = df.sort_values(by="name")
    df["item_id"] = df["name"].map(slugToId)
    df["order_type"] = df.get("order_type").str.lower()
    df.to_csv("allItemData.csv", index=False)

    try:
        os.remove("allItemDataBackup.csv")
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    try:
        main()
    finally:
        # sinon l'UI croit que le scraper tourne encore et refuse de le relancer
        config.setConfigStatus("runningStatisticsScraper", False)
