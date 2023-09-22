# Manual for the Project Template of Future-Portfolio Pairs Trading Algorithm
This strategy is built based on the mean-reverting property of stationary time
series. Considering the no-short ban on China's A-Share market, some stocks within
the specified stock pool will be selected to construct a portfolio first. Then some
futures will be adopted for hedging purposes.

The logical structure of this structure is described below in `section 1`. An
overview of the scripts and folders is in `section 2`. `section 3` lists the
environment settings of Python packages adopted in the development of this strategy.
For detailed definitions and illustrations of each function, please refer to the
comments attached in the codes.

## 1. Systematic Logic of Project

### 1.1. Input
The input should be a `str` type of date, formatting as `YYYY-MM-DD`.

If this is the first time running this program, initial amount of capital and margin
ratio for future trading will also be requested as input.

Other primary settings, including the stock pool, portfolio update frequency, model
parameters, and so on, are specified in the configuration file. Developers can make
changes if necessary.

### 1.2. Data Wrangling
The close price of stocks along with the future will be downloaded. It would take
around 10 minutes, depending on your Internet connection.

The downloaded/updated datasets will be saved in the `data` folder.

### 1.3. Construction of Stationary Series
_LASSO_ regression will be adopted to construct a stationary portfolio. To save
for transaction costs, this construction and re-construction will only be performed
on the first business day of each month.

Coefficients generated by _LASSO_ will be saved in the `output` folder for checking
+and usage later.

The downloaded/updated datasets will be saved in the `data` folder. The corresponding
contents of each file are illustrated below.

### 1.4. Model Fitting for Stationary Series
An `AR(1)` model will be trained using the historical data, for predicting the
long-run mean trend of the stationary series. A `GARCH(1, 1)` model will be trained
simultaneously for predicting the volatility of the stationary series.

These two models will be updated every time to better monitoring the market
situation and current state of our strategy. The predicted long-term mean and volatility
will be saved and updated to the `output` folder for checking and usage later.

### 1.5. Trading Signal Generating
With the estimated long-term mean and volatility of strategy, a two-sided boundary
will be generated for trading signal production. The logic for signal generating
is listed below:

- If the current paired series value is below the lower bound, the stock portfolio
should take a long position, while the future should take a short one.
- If the current paired series value is higher than the estimated long-term mean level,
all positions should be closed.




## 2. Overview of the Scripts and Folders
### `addpath.py`
Scripts for files paths. Created and called for better referring between scripts.
### `main.py`
The main file to call the algorithm. Run this file to generate straightforward
signals for trading every day. An input of date will be requested when running
this script.
### `README.md`
The current scripts. A manual for the project template.
### `algorithm`
Packed scripts and functions for this trading algorithm. Will be utilized to do
the computations.
### `config`
Configuration scripts.
### `data`
Downloaded price data.
### `output`
Output files during the algorithm. Including the parameters estimated during the
process and eventual results. The weight allocation for stocks will be stored in
the .csv file named `port_weights.csv` and the contract size will be stored in
the .csv dile named `future_size.csv`.


## 3. Python Environment and Package Settings
Anaconda is introduced for environment management. The requirements for packages
along with their versions are saved in the file `environment.yml`. Anaconda users
can create a conda virtual environment with the following command:
`conda env create --name <my-env-name> --file environment.yml`.