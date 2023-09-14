import pandas as pd
import numpy as np
import configparser

from timeit import default_timer as timer
from os.path import join

from addpath import output_path, configfile_path


# load the configurations
config = configparser.ConfigParser()
config.read(configfile_path)


def signal_generating_func(input_date_df, testing_df, portfolio_allocation_list, AR_param_df, GARCH_param_df):
    """
        Compare the current spread with the estimated equilibrium level and boundaries for generating signals.
    """
    print('-- Start generating signals.')
    tmp_time1 = timer()
    input_date_str = str(input_date_df.input_date.squeeze().date())

    # load the previous positions. if no existing record for positions, assume as the first day running this strategy
    try:
        previous_action_df = pd.read_csv(join(output_path, 'signal_df.csv'))
    except FileNotFoundError:
        previous_action_df = pd.DataFrame()
        previous_action_df['portfolio_position'] = pd.Series(0)
        previous_action_df['future_position'] = pd.Series(0)

    # specify the equilibrium level and boundaries to ease the comparison later
    signal_df = pd.DataFrame()
    signal_df['date'] = pd.Series(input_date_df.input_date)
    signal_df['volatility'] = GARCH_param_df.pred_volatility
    signal_df['equilibrium'] = AR_param_df.equilibrium
    boundary_ratio = float(config['parameters']['boundary_ratio'])
    signal_df['lower_bound'] = signal_df['equilibrium'] - boundary_ratio * signal_df['volatility']

    # compute the current spread
    Matrix = testing_df.drop(testing_df.columns[0:1], axis=1, inplace=False).to_numpy()
    test_portfolio = np.dot(Matrix, portfolio_allocation_list).flatten()
    test_futures = testing_df.iloc[:, 0].to_numpy().flatten()
    residuals_test = np.subtract(test_portfolio, test_futures)
    signal_df['future_value'] = test_futures
    signal_df['portfolio_value'] = test_portfolio
    signal_df['spread'] = residuals_test

    # compare the spread with the equilibrium level and boundaries
    previous_portfolio_position = previous_action_df['portfolio_position'].squeeze()
    previous_future_position = previous_action_df['future_position'].squeeze()
    spread = signal_df['spread'].squeeze()
    lower_bound = signal_df['lower_bound'].squeeze()
    equilibrium = signal_df['equilibrium'].squeeze()
    if previous_portfolio_position == 0 and previous_future_position == 0:
        if spread <= lower_bound:
            signal_df['portfolio_position'] = 1
            signal_df['future_position'] = -1
        else:
            signal_df['portfolio_position'] = 0
            signal_df['future_position'] = 0
    elif previous_portfolio_position == 1 and previous_future_position == -1:
        if spread <= equilibrium:
            signal_df['portfolio_position'] = 1
            signal_df['future_position'] = -1
        else:
            signal_df['portfolio_position'] = 0
            signal_df['future_position'] = 0
    else:
        print('-- Error with the current position for portfolio and future. Please check in the output files.')

    signal_df.to_csv(join(output_path, input_date_str, 'signal_df.csv'), index=False)

    tmp_time2 = timer()
    print('-- Finish generating signals. Time consumed: %.3fs.' % (tmp_time2 - tmp_time1))

    return signal_df
