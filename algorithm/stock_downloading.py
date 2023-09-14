import pandas as pd
import json
import requests
import urllib3
import tushare as ts

# this function is to get the corresponding code within the database for stocks
def getInnercode():
    urlstr = "https://stq.niuguwang.com/ft/innercode"
    header = {
        "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6",
        "Content-Type": "application/json"}
    Innercode = requests.get(urlstr, headers=header)
    Innercode_dict = json.loads(Innercode.content.decode("utf-8"))
    result = pd.DataFrame.from_dict(Innercode_dict["data"])
    return result

# this function is to download the data from database
def getAShrData(innercode, ktype, enddate, count, adj=True):
    """
    innercode : int
    ktype : int 1:5min; 2:15min; 3:30min; 4:60min; 5:1d; 6:1w; 9:1m, 11:1min
    enddate : str (not included)
    count : int
    adj : True/False
    """
    urlstr = "https://shqa.niuguwang.com/aquote/quote/kline.ashx?code={}&type={}&start={}&count={}&ex={}".format(
        innercode, ktype, enddate, count, int(adj))
    header = {
        "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6",
        "Content-Type": "application/json"}
    AShrData = requests.get(urlstr, headers=header)
    AShrData_dict = json.loads(AShrData.content.decode("utf-8"))
    result = pd.DataFrame.from_dict(AShrData_dict["timedata"])
    return result

# this function is to download the adjustment factors from the database
def getAdjFactor(ticker, startdate, enddate):
    startdate = startdate.strftime('%Y%m%d')
    enddate = enddate.strftime('%Y%m%d')
    tstoken = '5e8c8dc53d0b3a660989d14fc4b998cd865a27c9fe2e805246bfd9b3'
    pro = ts.pro_api(tstoken)
    adjfactor_df = pro.adj_factor(ts_code=ticker, start_date=startdate, end_date=enddate)
    adjfactor_df = adjfactor_df.set_index(["trade_date"])
    adjfactor_df = pd.DataFrame(adjfactor_df["adj_factor"])
    adjfactor_df.fillna(method="bfill", inplace=True)
    adjfactor_df.fillna(1, inplace=True)
    adjfactor_df.index = pd.to_datetime(adjfactor_df.index)
    adjfactor_df = adjfactor_df.sort_index()
    adjfactor_df = adjfactor_df.round(decimals=3)
    return adjfactor_df

# this function is to get the component of indexes
def getIndexComponents(idxcode, startdate, enddate):
    urlstr = "https://stq.niuguwang.com/NorthJg/GetNorthJg/hsweighthk"
    parms = {
        'sdate': startdate,
        'edate': enddate,
        'index_code': idxcode
    }
    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        'Spam': 'Eggs',
        'Connection': 'close'
    }
    urllib3.disable_warnings()
    IndexComponents = requests.get(urlstr, data=parms, headers=headers, verify=False, timeout=600)
    IndexComponents_dict = json.loads(IndexComponents.content.decode("utf-8"))
    result = pd.DataFrame.from_dict(IndexComponents_dict)
    return result
