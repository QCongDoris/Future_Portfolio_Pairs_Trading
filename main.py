import pandas as pd
import numpy as np
import configparser
import sys
import os
import math

from datetime import datetime
from os.path import join

import algorithm.data_wrangling as data_wrangling
import algorithm.model as model
from addpath import configfile_path, output_path
from algorithm.signal_generating import signal_generating_func

if __name__ == '__main__':
    import warnings
    warnings.filterwarnings("ignore")

    # load the configurations
    config = configparser.ConfigParser()
    config.read(configfile_path)
    initialization_status = int(config['parameters']['initialization_status'])
    future_index = config['parameters']['stock_pool']

    # request for inputs and prompt feedback messages to different cases
    input_status = True
    rebalance_status = False
    while input_status:
        input_date_str = input("Please specify the date for strategy generating (YYYY-MM-DD): ")
        try:
            input_date_df = datetime.strptime(input_date_str, "%Y-%m-%d")
            # check if the input day is the first business day of a month
            if np.is_busday(
                    input_date_str):  # if it is a business day, check if it is the first business day of a month
                if initialization_status == 1:
                    print('-- This is the first time running this strategy. Portfolio rebalance and model training '
                          'will be performed.')
                    initial_capital = input("Please specify the initial amount of capital for this strategy (e.g. "
                                            "1000000 stands for one million): ")
                    future_margin_ratio = input("Please specify the margin ratio for future trading (e.g. 0.15 stands "
                                                "for fifteen percentage): ")
                    rebalance_status = True
                elif np.busday_count(str(input_date_df.replace(day=1).date()), input_date_str) == 0:
                    print('-- The input date is the first business day of the month. Portfolio rebalance and model '
                          'training will be performed.')
                    rebalance_status = True
                else:
                    print('-- The input date is not the first business day of the month. Only model training will be '
                          'performed.')
                input_status = False
            else:
                print('-- The input date is not a business day. Please re-specify a date.')
        except ValueError:
            print('-- The input format is incorrect. Please re-specify.')
    input_date_df = data_wrangling.date_identification(input_date_str)

    # create the output path if it does not exist
    if not os.path.exists(join(output_path, input_date_str)):
        os.makedirs(join(output_path, input_date_str))

    # download data and do wrangling
    merged_df = data_wrangling.data_wrangling(input_date_df)

    # split for training set, validation set, and testing set
    training_df, testing_df = data_wrangling.training_testing_split(merged_df)
    # training_df, validation_df = data_wrangling.training_validation_split(training_df)

    # rebalance if the input date is the first business day of a month
    if rebalance_status:
        portfolio_allocation_list = model.lASSO_training(input_date_str, training_df)
    else:
        try:
            with open(join(output_path, 'LASSO_coef.txt'), 'r') as f:
                portfolio_allocation_list = f.readlines()
                portfolio_allocation_list = [item.replace('\n', '') for item in portfolio_allocation_list]
                portfolio_allocation_list = list(map(float, portfolio_allocation_list))
        except FileNotFoundError:
            print('-- There is no saved record for portfolio. Please check in the \'output\' folder.')
            sys.exit()

    # train the model using training set, and collect the estimated parameters
    AR_param_df, GARCH_param_df = model.model_training(input_date_str, training_df, portfolio_allocation_list)

    # generate signals
    signal_df = signal_generating_func(input_date_df, testing_df,
                                       portfolio_allocation_list, AR_param_df, GARCH_param_df)

    # compute values for stocks according to LASSO results
    portfolio_position = float(signal_df['portfolio_position'].squeeze())
    future_position = float(signal_df['future_position'].squeeze())
    port_weights_array = np.asarray(portfolio_allocation_list) * testing_df.iloc[:, 1:].to_numpy()

    # compute contract size for future
    if initialization_status == 1:
        future_size = math.floor(float(initial_capital) / ((1 + float(future_margin_ratio) + 0.01) * port_weights_array.sum()))
    else:
        future_size = float(config['parameters']['future_size'])
    with open(join(output_path, input_date_str, 'future_size.txt'), 'w') as f:
        f.write(f"-{future_size}")
        f.close()


    # transform stock values to weights
    portfolio_position = float(signal_df['portfolio_position'].squeeze())
    future_position = float(signal_df['future_position'].squeeze())
    port_weights_array = port_weights_array / port_weights_array.sum()
    port_weights_df = pd.DataFrame(port_weights_array * portfolio_position,
                                   columns=testing_df.columns[1:], index=[input_date_df.input_date]).T
    port_weights_df.to_csv(join(output_path, input_date_str, 'port_weights.csv'), index=True)

    print('-- Computation finished. Check \'port_weights.csv\' and \'future_size.txt\' in the \'output\' folder for '
          'the weight on each stock/index future.')

    # write the inputted data and computed parameters back to the configuration file
    initialization_status = 0
    config['inputs']['input_date'] = input_date_str
    config['inputs']['initial_capital'] = initial_capital
    config['inputs']['future_margin_ratio'] = future_margin_ratio
    config['parameters']['initialization_status'] = str(initialization_status)
    config['parameters']['future_size'] = str(future_size)
    with open(configfile_path, 'w') as configfile:
        config.write(configfile)

    # total_capital = signal_df['portfolio_value'].squeeze() / 0.75  # leave 25% of money for long back futures
    # weight = pd.DataFrame(
    #     np.multiply(testing_df.drop(testing_df.columns[0:1], axis=1, inplace=False).to_numpy() / total_capital,
    #                 portfolio_allocation_list).flatten(), index=testing_df.columns[1:], columns=[input_date_str])
    # weight.to_csv(join(output_path, 'weight.csv'), index=True)
