#!/usr/bin/env python
# coding:utf-8

##################################
# 仮装通貨の取引所間での差額を取得する
##################################

import json
import urllib3
import pycurl
from urllib.parse import urlencode
import logging
from datetime import datetime

urllib3.disable_warnings()

########## 定数 START ##########
ALERT_DIFF_ETH  = 10000;      # 基準差額
LINE_TOKEN      = "";  # LINE Notify トークン
LINE_NOTIFY_URL = "https://notify-api.line.me/api/notify"
LOG_NAME        = "Logging"
LOG_FILE_NAME   = "last_diff.log"
LOG_LEVEL       = 10
API_ZAIF_ETH    = 'https://api.zaif.jp/api/1/ticker/eth_jpy'
API_QUOINE_ETH  = 'https://api.quoine.com/products/code/CASH/ETHJPY'
########## 定数 END ##########

logger = None

# APIのレスポンスを引数に、jsonを辞書型で返す
def get_ask_bid_dict(res, ask_key, bid_key, name):
    if res.status == 200:
        json_dict = json.loads(res.data)
        ask = (json_dict[ask_key])
        bid = (json_dict[bid_key])
        return {"ask":ask, "bid":bid, "name":name}
    else:
        return None

# 一番高く売れる取引所を取得
def get_max_bid(dicts):
    name_max_bid = ""
    max_bid = 0
    is_first = True
    for d in dicts:
        if is_first:
            max_bid = d["bid"]
            name_max_bid = d["name"]
            is_first = False
        else:
            if d["bid"] > max_bid:
                max_bid = d["bid"]
                name_max_bid = d["name"]
    
    return {"name":name_max_bid, "bid":max_bid}

# 一番安く買える取引所を取得
def get_min_ask(dicts):
    name_min_ask = ""
    min_ask = 0
    is_first = True
    for d in dicts:
        if is_first:
            min_ask = d["ask"]
            name_min_ask = d["name"]
            is_first = False
        else:
            if d["ask"] < min_ask:
                min_ask = d["ask"]
                name_min_ask = d["name"]
    
    return {"name":name_min_ask, "ask":min_ask}

# LINEに通知
def send_message(message):
    post_data = {'message': message}
    postfields = urlencode(post_data)
    c = pycurl.Curl()
    c.setopt(pycurl.URL, LINE_NOTIFY_URL)
    c.setopt(pycurl.HTTPHEADER, ['Authorization: Bearer ' + LINE_TOKEN])
    c.setopt(pycurl.POSTFIELDS, postfields)
    c.perform()
    c.close()
    return

# ログを出力
def output_log(text):
    # 時間と価格差
    logger.info(datetime.now().strftime("%s") + "," + text)

# ログ出力初期設定
def get_logger():
    logger = logging.getLogger(LOG_NAME)
    logger.setLevel(LOG_LEVEL)
    fh = logging.FileHandler(LOG_FILE_NAME)
    logger.addHandler(fh)
    return logger

###################################
# メイン処理
###################################
if __name__ == '__main__':

    # ログ出力初期設定
    logger = get_logger()

    # APIで情報を取得
    http = urllib3.PoolManager()
    zf_res = http.request('GET', API_ZAIF_ETH)
    qn_res = http.request('GET', API_QUOINE_ETH)

    # jsonをマップ型に変換
    zf_dict = get_ask_bid_dict(zf_res, "ask", "bid", "ZAIF")
    qn_dict = get_ask_bid_dict(qn_res, "market_ask", "market_bid", "QUOINEX")

    # 価格差判定（情報を取得できた場合のみ実施）
    if zf_dict is not None and qn_dict is not None:

        dicts = [zf_dict, qn_dict]

        # 価格一覧表示
        for d in dicts:
            print("(" + d["name"] + ") bid:" + str(d["bid"]) + " ask:" + str(d["ask"]))
            
        # 価格差を取得
        max_bid_dict = get_max_bid(dicts)
        min_ask_dict = get_min_ask(dicts)

        if max_bid_dict["name"] != min_ask_dict["name"]:
            # コンソールに結果表示
            message = min_ask_dict["name"] + "で買って、"
            message += max_bid_dict["name"] + "で売れば、"
            message += str(int(max_bid_dict["bid"] - min_ask_dict["ask"])) + "円の儲け"
            print (message)

            # 差額を取得
            diff = int(max_bid_dict["bid"] - min_ask_dict["ask"])
            
            # 基準差額より大きい場合
            if diff > ALERT_DIFF_ETH:

                # ログファイルから前回の差額を取得
                file = open(LOG_FILE_NAME)
                data = file.read()
                file.close()
                lines = data.split('\n')
                
                last_diff = 0
                last_diff_time = 0
                for i, l in enumerate(lines):
                    if i == len(lines) - 2:
                        line_arr = l.split(',')
                        last_diff = int(line_arr[1])

                # 前回の差額が基準額より低い場合
                if last_diff <= ALERT_DIFF_ETH:
                    # LINEに通知
                    send_message(message)

            # 差額をログファイルに出力
            output_log(str(diff))
