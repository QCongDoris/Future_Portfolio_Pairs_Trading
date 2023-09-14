import datetime
import json
import requests
import traceback
import pandas as pd

def get_HisMainContract(variety=None, start=None, end=None):
    start_ = str(datetime.datetime.strptime(start, '%Y-%m-%d'))[:19]
    start_ = start_.replace('-', '').replace(':', '').replace(' ', '')
    end_ = str(datetime.datetime.strptime(end, '%Y-%m-%d'))[:19]
    end_ = end_.replace('-', '').replace(':', '').replace(' ', '')
    body = {'varietyCode': variety, 'begin': int(start_), 'end': int(end_)}
    try:
        url = "https://apigateway.inquantstudio.com/api/BasicData/GetHisMain"
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.90 Safari/537.36",
            "Content-Type": "application/json"}
        response = requests.post(url, data=json.dumps(body), headers=headers)
        response.close()
    except Exception:
        print(traceback.format_exc())
    else:
        try:
            response_json = json.loads(response.content.decode())
            if response_json.get('error_no') == 0:
                return pd.DataFrame(response_json.get('data'))
            else:
                return response_json.get('error_info')
        except:
            print(traceback.format_exc())


def exchange2num(exchange):
    if exchange is None:
        return 4
    elif exchange == 'CFFEX':  # 中金所
        return 3
    elif exchange == 'SHFE':  # 上期所
        return 4
    elif exchange == 'DCE':  # 大商所
        return 5
    elif exchange == 'CZCE':  # 郑商所
        return 6
    elif exchange == 'INE':  # 上海国际能源交易中心
        return 15


def freq2dataType(freq=None):
    if freq is None:
        return 60
    elif freq == '10s':
        return 10
    elif freq == '1m':
        return 60
    elif freq == '5m':
        return 5 * 60
    elif freq == '15m':
        return 15 * 60
    elif freq == '30m':
        return 30 * 60
    elif freq == '60m':
        return 60 * 60
    elif freq == '1d':
        return 60 * 60 * 24
    elif freq == '1w':
        return 60 * 60 * 24 * 7
    else:
        return 60 * 60 * 24


def get_hisBar(symbol=None, exchange=None, freq=None, start=None, end=None, count=None):
    exchange_ = exchange2num(exchange)
    dataType = freq2dataType(freq=freq)
    url = ''
    body = {"symbol": symbol, "exchange": exchange_, "dataType": dataType, "dataSource": 1}
    if start and end and not count:
        if start == end and dataType == 86400:
            end_ = str(datetime.datetime.strptime(end, '%Y-%m-%d') + datetime.timedelta(days=1))[:19]
        else:
            end_ = end
        begin = start.replace('-', '').replace(' ', '').replace(':', '')
        end__ = end_.replace('-', '').replace(' ', '').replace(':', '')
        body['begin'] = begin
        body['end'] = end__
        url = "https://apigateway.inquantstudio.com/api/MarketData/GetHisBar"
    if not start and not end and count:
        body['count'] = count
        url = "https://apigateway.inquantstudio.com/api/MarketData/GetLastBar"
    if not start and end and count:
        end_ = end.replace('-', '').replace(' ', '').replace(':', '')
        if len(end_) == 8:
            end_ += '000000'
        if dataType == 86400 and count == 1:
            count_ = 1
            end_ = end_.replace('-', '').replace(' ', '').replace(':', '')
        else:
            count_ = count
        body['end'] = end_
        body['count'] = count_
        url = "https://apigateway.inquantstudio.com/api/MarketData/GetPreviousBar"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6",
            "Content-Type": "application/json"}
        response = requests.post(url, data=json.dumps(body), headers=headers)
        response.close()
    except Exception:
        print(traceback.format_exc())
        return None
    else:
        response = response.content.decode()
        response_json = json.loads(response)
        data = response_json.get('data')
        df_data = pd.DataFrame(data)
        if df_data.empty:
            return df_data
        df_data.columns = ['symbol', 'exchange', 'bar_type', 'time', 'pre_close', 'open', 'high', 'low', 'close',
                           'volume',
                           'turnover', 'open_interest', 'settlement']
        if start and end and not count:
            if start == end and dataType == 86400:
                begin = start.replace('-', '').replace(' ', '').replace(':', '')
                end = end.replace('-', '').replace(' ', '').replace(':', '')
                if len(begin) == 8:
                    begin += '000000'
                if len(end) == 8:
                    end += '000000'
                df_data = df_data[(df_data["time"] >= int(begin)) & (df_data["time"] <= int(end))]
        if not start and end and count:
            if dataType == 86400 and count == 1:
                df_data = df_data[-1:]
        df_data_ = df_data.sort_values(by='time').reset_index(drop=True)
        return df_data_
