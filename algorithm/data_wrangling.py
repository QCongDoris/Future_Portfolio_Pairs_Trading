import pandas as pd
import numpy as np
import configparser
import sys
import os

from timeit import default_timer as timer
from os.path import join
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sklearn.model_selection import train_test_split

from addpath import data_path, configfile_path
from algorithm.future_downloading import get_hisBar
from algorithm.stock_downloading import getIndexComponents, getInnercode, getAShrData, getAdjFactor

# load the configurations
config = configparser.ConfigParser()
config.read(configfile_path)


def date_identification(input_date_str):
    """
        Identify the input date.
        The return of this function will be a dictionary containing the datetime format of original input string,
    along with other organized attributes like starting year, end year, and so on.
    """
    # create the data path if it does not exist
    if not os.path.exists(join(data_path, input_date_str)):
        os.makedirs(join(data_path, input_date_str))

    input_date = datetime.strptime(input_date_str, "%Y-%m-%d")
    start_date = input_date + relativedelta(years=-1)  # training set should start from 1 year before
    input_date_df = pd.DataFrame([{'input_date': input_date, 'start_date': start_date, 'end_date': input_date}])
    return input_date_df


def data_downloading_fully(input_date_df):
    """
        Download all the future price and stock price from one year ago to the given date.
        The return of this function will be a tuple containing three data frames: (futures, close, adj_df).
        Raw close price for stocks, close price for future, adjustment factor, and adjusted price will be saved
    in data_path.
    """
    # download future data
    print('---- Start downloading future price data.')
    tmp_time1 = timer()
    input_date_str = str(input_date_df.input_date.squeeze().date())
    # load the code for future
    future_code = config['parameters']['future_code']
    futures_start_date = str(input_date_df.start_date.squeeze().date())
    futures_end_date = str(input_date_df.end_date.squeeze().date())
    future_data = get_hisBar(symbol=future_code, exchange='CFFEX', freq='1d', start=futures_start_date,
                             end=futures_end_date)
    futures = future_data[['time', 'close']]
    futures.rename(columns={'time': 'times'}, inplace=True)
    futures['times'] = (futures['times'] / 10e5).apply(int).apply(lambda x: pd.to_datetime(str(x), format='%Y%m%d'))
    futures = futures.set_index('times')
    futures.to_csv(join(data_path, input_date_str, 'futures.csv'))
    tmp_time2 = timer()
    print('---- Finish downloading future price data. Time consumed: %.3fs.' % (tmp_time2 - tmp_time1))

    # load the stock pool and trading dates.
    print('---- Start loading the stock pool information.')
    tmp_time1 = timer()
    # load the stock pool indicator
    stock_pool = config['parameters']['stock_pool']
    if stock_pool in ['000300.SH', '000905.SH']:
        component_start_date = input_date_df.start_date.squeeze().date()
        IndexComponents = getIndexComponents(stock_pool, str(component_start_date), futures_end_date)
        while IndexComponents.size == 0:
            print('---- No recent index components data available. Earlier components will be introduced.')
            component_start_date = component_start_date + relativedelta(months=-6)
            IndexComponents = getIndexComponents(stock_pool, str(component_start_date), futures_end_date)
            if IndexComponents.size > 0:
                print('---- Components starting from %s introduced.' % str(component_start_date))
        stk_list = IndexComponents['ticker'].to_list()
        stk_list = list(set(stk_list))
        del IndexComponents
    else:
        print(
            '---- The stock pool specified in the configuration file is improper. Please choose between \"000300.SH\" and \"000905.SH\".')
        sys.exit()
    tmp_time2 = timer()
    print('---- Finish loading the stock pool information. Time consumed: %.3fs, pool length: %d.'
          % (tmp_time2 - tmp_time1, len(stk_list)))

    # download stock prices and adjustment factors, and then do dividend adjustment
    print('---- Start downloading stock prices.')
    tmp_time1 = timer()
    Innercode = getInnercode()
    close_dict = {}
    adj_dict = {}
    startdate = input_date_df.start_date.squeeze().date()  # download from this day
    enddate = (input_date_df.end_date.squeeze() + relativedelta(days=1)).date()
    # download until this day (not included). will be used for downloading stock prices
    enddate_adj_fac = input_date_df.end_date.squeeze().date()
    # download until this day (included). will be used for downloading adjustment factors
    count = (enddate - startdate).days  # count the number of days to download
    enddate = enddate.strftime('%Y%m%d000000')
    ktype = 5

    for stk in stk_list:
        # download for stock prices
        loc = stk_list.index(stk)
        if loc % 10 == 0:
            print('Working on stock No. %d: %s' % (loc + 1, stk))

        stock = stk
        innercode = int(Innercode.loc[Innercode["TradingCode"] == stock, "InnerCode"])
        AShrData = getAShrData(innercode, ktype, enddate, count, adj=False)
        AShrData['times'] = pd.to_datetime(AShrData['times'])
        AShrData = AShrData.set_index('times')
        AShrData = AShrData.reindex(index=AShrData.index[::-1])
        AShrData = AShrData.loc[startdate:enddate, ]
        close_dict[stk] = AShrData['nowv'].astype('int64') / 100

        # download for adjustment factors
        adj_dict[stk] = getAdjFactor(stk, startdate, enddate_adj_fac)

    # reorganize the dictionaries and convert them into dataframes. forward fill used
    close = pd.concat(close_dict, axis=1, join='outer')
    adj_df = pd.concat(adj_dict, axis=1, join='outer').bfill()
    adj_df.columns = close.columns

    # drop the columns with too many Nan values
    close = close.dropna(axis=1, thresh=0.7 * close.shape[0]).ffill()
    close.to_csv(join(data_path, input_date_str, 'close.csv'))
    adj_df = adj_df.reindex(index=close.index, method='bfill').reindex(columns=close.columns)
    adj_df.to_csv(join(data_path, input_date_str, 'adj_fac.csv'))

    tmp_time2 = timer()
    print('---- Finish downloading stock prices. Time consumed: %.3fs.' % (tmp_time2 - tmp_time1))

    return futures, close, adj_df


def price_adjustment(close, adj_df, input_date_str):
    """
        Do dividend adjustment for raw price data.
        The return of this function will be a data frame of adjusted close price.
        Raw close price for stocks, close price for future, adjustment factor, and adjusted price will be saved
    in data_path.
    """
    # do dividend adjustment
    end_fac = adj_df.iloc[-1]
    adj_fac = adj_df.div(end_fac, axis=1)
    adj_close = np.multiply(close, adj_fac)
    adj_close.to_csv(join(data_path, input_date_str, 'adj_close.csv'))
    return adj_close


def data_merging(futures_df, stocks_df, input_date_str):
    """
        Merge the future price and stock price.
    """
    print('---- Start merging future price and stock prices.')
    tmp_time1 = timer()

    # delete the row indexed '2020-10-08' if exists
    if pd.to_datetime('2020-10-08') in stocks_df.index.values:
        stocks_df = stocks_df[stocks_df.index != '2020-10-08']

    # re-order the columns to keep them consistent along different times
    stocks_df.columns = stocks_df.columns.str.replace('.SH', '').str.replace('.SZ', '')
    stocks_df = stocks_df.sort_index(axis=1, ascending=False)
    stocks_df.columns = [col + ('.SH' if int(col) >= 600000 else '.SZ') for col in stocks_df.columns]
    stocks_df.to_csv(join(data_path, input_date_str, 'sorted_stocks.csv'))

    # merge the adjusted close price after future price
    merged_df = futures_df.join(stocks_df)
    merged_df.rename(columns={'close': 'future'}, inplace=True)
    merged_df.to_csv(join(data_path, input_date_str, 'merged_data.csv'), index=False)
    tmp_time2 = timer()
    print('---- Finish merging prices. Time consumed: %.3fs.' % (tmp_time2 - tmp_time1))

    return merged_df


def data_wrangling(input_date_df):
    """
        Download data and perform wrangling according to whether existing price files detected.
    """
    input_date_str = str(input_date_df.input_date.squeeze().date())
    futures_df, close_df, adj_df = data_downloading_fully(input_date_df)
    # close_df = pd.read_csv(join(data_path, input_date_str, 'close.csv'), dtype=float, index_col=0, parse_dates=[0])
    # adj_df = pd.read_csv(join(data_path, input_date_str, 'adj_fac.csv'), dtype=float, index_col=0, parse_dates=[0])
    # futures_df = pd.read_csv(join(data_path, input_date_str, 'futures.csv'), dtype=float, index_col=0, parse_dates=[0])

    # do dividend adjustment and merging together
    adj_close_df = price_adjustment(close_df, adj_df, input_date_str)
    merged_df = data_merging(futures_df, adj_close_df, input_date_str)
    merged_df.rename(columns={'close': 'future'}, inplace=True)

    # deal with missing values
    if merged_df.isnull().values.ravel().sum() < 0.1 * merged_df.shape[0]:
        merged_df = merged_df.dropna(axis=0, how='any')
    else:
        merged_df = merged_df.dropna(axis=1, how='any')

    return merged_df


def training_testing_split(data):
    """
        Split the training set and testing set.
    """
    print('-- Start splitting the training and testing set.')
    tmp_time1 = timer()
    training, testing = train_test_split(data, test_size=1, shuffle=False)
    tmp_time2 = timer()
    print('-- Finish splitting the training and testing set. Time consumed: %.3fs.' % (tmp_time2 - tmp_time1))

    return training, testing


def training_validation_split(data):
    """
        Split the training set and validation set.
    """
    # load from the configuration file
    validation_size = config['parameters']['update_window_size']

    print('-- Start splitting the training and validation set.')
    tmp_time1 = timer()
    training, validation = train_test_split(data, test_size=validation_size, shuffle=False)
    tmp_time2 = timer()
    print('-- Finish splitting the training and validation set. Time consumed: %.3fs.' % (tmp_time2 - tmp_time1))

    return training, validation
