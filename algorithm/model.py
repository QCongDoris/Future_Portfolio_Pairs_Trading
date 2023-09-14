import numpy as np
import pandas as pd
import configparser

from os.path import join
from sklearn.linear_model import Lasso
from statsmodels.tsa.ar_model import AutoReg
from arch import arch_model
from timeit import default_timer as timer

from addpath import configfile_path, output_path

# load the configurations
config = configparser.ConfigParser()
config.read(configfile_path)


def lASSO_training(input_date_str, training_df):
    """
        Train a LASSO model for constructing a stationary time series based on stock portfolio and future.
    """
    print('-- Start portfolio rebalancing.')
    tmp_time1 = timer()
    alpha = float(config['parameters']['LASSO_alpha'])

    # do a LASSO with intercept = 0, alpha read from configuration file
    lin = Lasso(alpha=alpha, fit_intercept=False, precompute=True, max_iter=10000,
                positive=True, random_state=9999, selection='random')
    lin.fit(training_df.iloc[:, 1:].values, training_df.iloc[:, 0].values)
    coef_list = list(lin.coef_)  # coefficients

    # save the coefficients of LASSO to a .txt file
    with open(join(output_path, input_date_str, 'LASSO_coef.txt'), 'w') as f:
        for coef in coef_list:
            f.write(f"{coef}\n")
        f.close()

    tmp_time2 = timer()
    print('-- Finish portfolio rebalancing. Time consumed: %.3fs.' % (tmp_time2 - tmp_time1))

    return coef_list


def model_training(input_date_str, training_df, portfolio_allocation_list):
    """
        Train an AR(p) model for mean trend, and a GARCH(p, q) model for volatility.
    """
    print('-- Start training models.')
    tmp_time1 = timer()
    AR_p = int(config['parameters']['AR_p'])
    GARCH_p = int(config['parameters']['GARCH_p'])
    GARCH_q = int(config['parameters']['GARCH_q'])

    # compute training residuals
    Matrix = training_df.drop(training_df.columns[0:1], axis=1, inplace=False).to_numpy()
    train_portfolio = np.dot(Matrix, portfolio_allocation_list).flatten()
    train_futures = training_df.iloc[:, 0].to_numpy().flatten()
    residuals_train = np.subtract(train_portfolio, train_futures)

    # train an AR model for mean trend using the training data
    model_AR = AutoReg(residuals_train, lags=AR_p, trend='t')
    model_AR_fitted = model_AR.fit()
    # adf = adfuller(residuals_train, maxlag=AR_p)

    # collect estimated value from the AR model for mean trend prediction
    alpha = model_AR_fitted.params[0]
    beta = model_AR_fitted.params[1]
    sigma2 = model_AR_fitted.sigma2
    equilibrium = alpha / (1 - beta)
    sd = np.sqrt(sigma2 / (1 - beta ** 2))
    AR_param_df = pd.DataFrame([{'alpha': alpha, 'beta': beta, 'sigma2': sigma2, 'equilibrium': equilibrium, 'sd': sd}])
    AR_param_df.to_csv(join(output_path, input_date_str, 'AR_param_df.csv'), index=False)

    # train a GARCH model for volatility bounds using the training data
    model_GARCH = arch_model(residuals_train, p=GARCH_p, q=GARCH_q)
    model_GARCH_fitted = model_GARCH.fit(disp='off')

    # collect estimated volatility from the GARCH model
    pred_result = model_GARCH_fitted.forecast(horizon=1)
    pred_volatility = np.sqrt(pred_result.variance.values[-1, :][0])
    GARCH_param_df = pd.DataFrame([{'pred_volatility': pred_volatility}])
    GARCH_param_df.to_csv(join(output_path, input_date_str, 'GARCH_param_df.csv'), index=False)

    tmp_time2 = timer()
    print('-- Finish training models. Time consumed: %.3fs.' % (tmp_time2-tmp_time1))

    return AR_param_df, GARCH_param_df



