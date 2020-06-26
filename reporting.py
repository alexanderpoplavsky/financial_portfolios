
import pandas as pd
import numpy as np
import pickle


date_str = "Date"
operation_str = "Operation"
cash_flow_str = "Cash Flow"
balance_str = "Balance"
record_str = "Record"
deposit_str = "Deposit"
withdraw_str = "Withdraw"
buy_str = "Buy"
sell_str = "Sell"
bank_str = "Bank"
portfolio_str = "Portfolio"
isin_str = "ISIN"
currency_str = "Currency"
rate_str = "Exchange Rate"
title_str = "Title"
quantity_str = "Quantity"
price_str = "Price"
average_price_str = "Average Buy Price"
nav_str = "NAV"
commission_str = "Commission, %"
value_str = "Value"
maturity_str = "Maturity"
amount_str = "Amount"
weight_str = "Weight, %"
cash_str = "Cash"
coupon_str = "Coupon"
pnl_str = "PnL"
irr_str = "MWRR, %"
annualised_return_str = "Annualised Return, %"


def round_column(s, digits=2):
    return s.astype(np.float).round(digits)

def percentage_column(s, digits=2):
    return (s.astype(np.float) * 100).round(digits)

def exchange_rates(dates, pair, source):
    rates = pickle.load(open("rates.pickle", "rb" ))
    return rates.asof(dates)[pair]
    

class Reporting:
    
    def __init__(self, date, portfolio_id, initial_balance, currency):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.currency = currency
        self.portfolio_id = portfolio_id
        self.portfolio = pd.DataFrame([], columns=[isin_str, currency_str, maturity_str, quantity_str, price_str, average_price_str, rate_str, amount_str, weight_str])
        self.portfolio.index.name = title_str
        self.portfolio.loc[cash_str] = ["", currency, "", initial_balance, 1,  1, 1, initial_balance, 1]
        self.current_account = pd.DataFrame([[pd.to_datetime(date), deposit_str, initial_balance, initial_balance, deposit_str]],
                                   columns=[date_str, operation_str, cash_flow_str, balance_str, record_str])
        self.buysell = pd.DataFrame([], columns=[portfolio_str, bank_str, date_str, isin_str, currency_str, rate_str, title_str, operation_str, quantity_str, price_str, nav_str, commission_str, value_str])
        self.asset_log = {}
    
    def __normalise(self):
        self.portfolio.loc[cash_str, amount_str] = self.balance
        self.portfolio[weight_str] = self.portfolio[amount_str] / self.portfolio[amount_str].sum()
        
    def __reorder(self):
        index = [x for x in self.portfolio.index if x!=cash_str]
        index += [cash_str]
        self.portfolio = self.portfolio.reindex(index=index)
    
    def __update_cash(self):
        self.portfolio.loc[cash_str, quantity_str] = self.balance
        self.portfolio.loc[cash_str, amount_str] = self.balance
    
    def __clean(self):
        self.portfolio = self.portfolio[self.portfolio[amount_str] > 0.01]
        self.portfolio.loc[cash_str, maturity_str] = ""
        self.portfolio.loc[cash_str, quantity_str] = 1
        self.portfolio.loc[cash_str, price_str] = 1
        self.portfolio.loc[cash_str, average_price_str] = 1
        self.portfolio.loc[cash_str, rate_str] = 1
        self.portfolio.loc[cash_str, currency_str] = self.currency
        self.portfolio.loc[cash_str, isin_str] = ""
        
    def deposit(self, date, amount):
        self.balance += amount
        self.current_account.loc[len(self.current_account)] = [pd.to_datetime(date), deposit_str, amount, self.balance, deposit_str]
        self.__update_cash()
        self.__normalise()
        
    def withdraw(self, date, amount):
        if self.balance < amount:
            amount = self.balance
            self.balance = 0
        else:
            self.balance -= amount
        self.current_account.loc[len(self.current_account)] = [pd.to_datetime(date), withdraw_str, amount, self.balance, withdraw_str]
        self.__update_cash()
        self.__normalise()
    
    def buy(self, asset_info, quantity):
        rate = 1
        if asset_info["currency"] != "EUR":
            rate = exchange_rates(pd.to_datetime(asset_info["date"]), asset_info["currency"]+"EUR", None)
        amount = (1 + asset_info["commission"]) * quantity * asset_info["price"] * rate
        if amount > self.balance:
            amount = self.balance
            self.balance = 0
        else:
            self.balance -= amount
        if amount < 0.01: return
        record_data_str = buy_str + ": " + asset_info["title"] + " ISIN: " + asset_info["isin"]
        self.current_account.loc[len(self.current_account)] = [pd.to_datetime(asset_info["date"]), buy_str, amount, self.balance, record_data_str]
        buysell_enrty = {portfolio_str: self.portfolio_id,
                       bank_str: asset_info["bank"],
                       date_str: pd.to_datetime(asset_info["date"]),
                       isin_str: asset_info["isin"],
                       currency_str: asset_info["currency"],
                       rate_str: rate,
                       title_str: asset_info["title"],
                       operation_str: buy_str,
                       quantity_str: quantity,
                       price_str: asset_info["price"],
                       nav_str: asset_info["nav"],
                       commission_str: asset_info["commission"],
                       value_str: amount}
        self.buysell.loc[len(self.buysell)] = buysell_enrty
        if asset_info["title"] not in self.asset_log:
            self.asset_log[asset_info["title"]] = {"isin": asset_info["isin"], "currency": asset_info["currency"],
                          "cashflow": pd.DataFrame([], columns=[price_str, amount_str])}
        self.asset_log[asset_info["title"]]["cashflow"].loc[pd.to_datetime(asset_info["date"]), amount_str] = -amount
        self.asset_log[asset_info["title"]]["cashflow"].loc[pd.to_datetime(asset_info["date"]), price_str] = asset_info["price"]
        cashflow = self.asset_log[asset_info["title"]]["cashflow"]
        cashflow_buy = cashflow[cashflow[amount_str] < 0]
        average_price = cashflow_buy.prod(axis=1).sum() / cashflow_buy[amount_str].sum()
        if asset_info["title"] not in self.portfolio.index:
            self.portfolio.loc[asset_info["title"]] = [asset_info["isin"], asset_info["currency"], asset_info["maturity"], quantity, asset_info["price"], average_price, rate, amount, 0]
        else:
            self.portfolio.loc[asset_info["title"], quantity_str] += quantity
            self.portfolio.loc[asset_info["title"], price_str] = asset_info["price"]
            self.portfolio.loc[asset_info["title"], average_price_str] = average_price
            self.portfolio.loc[asset_info["title"], rate_str] = rate
            self.portfolio.loc[asset_info["title"], amount_str] = self.portfolio.loc[asset_info["title"], quantity_str] * asset_info["price"] * rate
        self.__update_cash()
        self.__normalise()
        self.__reorder()
        self.__clean()
        
    def sell(self, asset_info, quantity):
        if asset_info["title"] not in self.portfolio.index: return
        rate = 1
        if asset_info["currency"] != "EUR":
            rate = exchange_rates(pd.to_datetime(asset_info["date"]), asset_info["currency"]+"EUR", None)
        quantity = min(quantity, self.portfolio.loc[asset_info["title"], quantity_str])        
        amount = (1 + asset_info["commission"]) * quantity * asset_info["price"] * rate
        if amount < 0.01: return
        self.balance += amount
        record_data_str = sell_str + ": " + asset_info["title"] + " ISIN: " + asset_info["isin"]
        self.current_account.loc[len(self.current_account)] = [pd.to_datetime(asset_info["date"]), sell_str, amount, self.balance, record_data_str]
        buysell_enrty = {portfolio_str: self.portfolio_id,
                       bank_str: asset_info["bank"],
                       date_str: pd.to_datetime(asset_info["date"]),
                       isin_str: asset_info["isin"],
                       currency_str: asset_info["currency"],
                       rate_str: rate,
                       title_str: asset_info["title"],
                       operation_str: sell_str,
                       quantity_str: quantity,
                       price_str: asset_info["price"],
                       nav_str: asset_info["nav"],
                       commission_str: asset_info["commission"],
                       value_str: amount}
        self.buysell.loc[len(self.buysell)] = buysell_enrty
        self.asset_log[asset_info["title"]]["cashflow"].loc[pd.to_datetime(asset_info["date"]), amount_str] = amount
        self.asset_log[asset_info["title"]]["cashflow"].loc[pd.to_datetime(asset_info["date"]), price_str] = asset_info["price"]
        self.portfolio.loc[asset_info["title"], quantity_str] -= quantity
        self.portfolio.loc[asset_info["title"], price_str] = asset_info["price"]
        self.portfolio.loc[asset_info["title"], rate_str] = rate
        self.portfolio.loc[asset_info["title"], amount_str] = self.portfolio.loc[asset_info["title"], quantity_str] * asset_info["price"] * rate
        self.portfolio.loc[cash_str, quantity_str] = self.balance
        self.portfolio.loc[cash_str, amount_str] = self.balance        
        self.__update_cash()
        self.__normalise()
        self.__reorder()
        self.__clean()
        
    def interest(self, interest_info):
        rate = 1
        if interest_info["currency"] != "EUR":
            rate = exchange_rates(pd.to_datetime(interest_info["date"]), interest_info["currency"]+"EUR", None)
        self.balance += interest_info["amount"] * rate
        interest_str = "Dividend / Coupon"
        record_data_str = "Title: " + interest_info["isin"] + " " + interest_info["currency"] + " Qty: " + str(interest_info["quantity"]) + " (" + interest_info["title"] + ")"
        self.current_account.loc[len(self.current_account)] = [pd.to_datetime(interest_info["date"]), interest_str, interest_info["amount"] * rate, self.balance, record_data_str]
        self.__normalise()        
        if interest_info["title"] not in self.asset_log:
            self.asset_log[interest_info["title"]] = {"isin": interest_info["isin"], "currency": interest_info["currency"],
                          "cashflow": pd.DataFrame([], columns=[interest_info["title"]])}
        self.asset_log[interest_info["title"]]["cashflow"].loc[pd.to_datetime(interest_info["date"]), amount_str] = interest_info["amount"] * rate
        self.asset_log[interest_info["title"]]["cashflow"].loc[pd.to_datetime(interest_info["date"]), price_str] = 0        
        self.__update_cash()
        self.__normalise()
    
    def __portfolio_total(self):
        portfolio_total = {amount_str: self.portfolio[amount_str].sum(), 
                           weight_str: self.portfolio[weight_str].sum()}
        return portfolio_total
    
    def current_account_table(self):
        tmp = self.current_account.copy()
        tmp[cash_flow_str] = round_column(tmp[cash_flow_str], 2)
        tmp[balance_str] = round_column(tmp[balance_str], 2)
        return tmp
    
    def buysell_table(self):
        tmp = self.buysell.copy()
        tmp[quantity_str] = round_column(tmp[quantity_str], 2)
        tmp[price_str] = round_column(tmp[price_str], 2)
        tmp[nav_str] = round_column(tmp[nav_str], 2)
        tmp[commission_str] = percentage_column(tmp[commission_str], 2)
        tmp[value_str] = round_column(tmp[value_str], 2)
        return tmp
    
    def positions_table(self, date, current_prices):
        self.update_positions(date, current_prices)
        tmp = self.portfolio.copy()
        tmp[quantity_str] = round_column(tmp[quantity_str], 2)
        tmp[price_str] = round_column(tmp[price_str], 2)
        tmp[average_price_str] = round_column(tmp[average_price_str], 2)
        tmp[rate_str] = round_column(tmp[rate_str], 4)
        tmp[amount_str] = round_column(tmp[amount_str], 2)
        tmp[weight_str] = percentage_column(tmp[weight_str], 2)
        tmp_total = self.__portfolio_total()
        tmp_total[amount_str] = round(tmp_total[amount_str], 2)
        tmp_total[weight_str] = round(tmp_total[weight_str] * 100, 2)
        return tmp, tmp_total
        
    def returns_table(self, date, current_prices):
        self.update_positions(date, current_prices)
        df = pd.DataFrame([], columns=[isin_str, currency_str, coupon_str, pnl_str, irr_str, annualised_return_str], index=self.asset_log.keys())
        resampled_list = []
        ii_list = []
        for asset in self.asset_log:
            df.loc[asset, isin_str] = self.asset_log[asset]["isin"]
            df.loc[asset, currency_str] = self.asset_log[asset]["currency"]
            df.loc[asset, coupon_str] = 0
            cashflow = self.asset_log[asset]["cashflow"][amount_str].copy()
            if asset in self.portfolio.index:
                cashflow.loc[pd.to_datetime(date)] = self.portfolio.loc[asset, amount_str]
            ii = cashflow.iloc[0]
            ii_list.append(ii)
            resampled = cashflow.iloc[1:].resample("y").sum()
            resampled.name = asset
            resampled_list.append(resampled)
            irr = np.irr([ii] + [x for x in resampled.values])
            df.loc[asset, irr_str] = irr
            df.loc[asset, pnl_str] = cashflow.sum()
            delta_years = (cashflow.index[-1] - cashflow.index[0]).days / 252 
            df.loc[asset, annualised_return_str] = cashflow.sum() / -cashflow.iloc[0] / delta_years
            df.loc[asset, coupon_str] = 0
        resampled_portfolio = pd.concat(resampled_list, axis=1).sum(axis=1)            
        irr_portfolio = np.irr([np.sum(ii_list)] + [x for x in resampled_portfolio.values])
        pnl_portfolio = df[pnl_str].sum()
        ar_portfolio = self.portfolio[amount_str].sum() / self.initial_balance - 1 
        ar_portfolio /= delta_years
        df_total = {coupon_str: df[coupon_str].sum(),
                    pnl_str: pnl_portfolio,
                    irr_str: irr_portfolio,
                    annualised_return_str: ar_portfolio}
        df[coupon_str] = round_column(df[coupon_str], 2) 
        df[pnl_str] = round_column(df[pnl_str], 2) 
        df[irr_str] = percentage_column(df[irr_str], 2)
        df[annualised_return_str] = percentage_column(df[annualised_return_str], 2)      
        df_total[coupon_str] = round(df_total[coupon_str], 2)
        df_total[pnl_str] = round(df_total[pnl_str], 2)
        df_total[irr_str] = round(df_total[irr_str] * 100, 2)
        df_total[annualised_return_str] = round(df_total[annualised_return_str] * 100, 2)
        return df, df_total
    
    def update_positions(self, date, current_prices):
        for asset in current_prices:
            if asset in self.portfolio.index:
                if self.portfolio.loc[asset, currency_str] != "EUR":
                    self.portfolio.loc[asset, rate_str] = exchange_rates(date, self.portfolio.loc[asset, currency_str]+"EUR", None)
                self.portfolio.loc[asset, price_str] = current_prices[asset]
                self.portfolio.loc[asset, amount_str] = current_prices[asset] * self.portfolio.loc[asset, quantity_str] * self.portfolio.loc[asset, rate_str]
#                cashflow = self.asset_log[asset]["cashflow"].copy()
#                cashflow = cashflow[cashflow[price_str] > 0]
#                self.asset_log[asset]["cashflow"].loc[pd.to_datetime(date), price_str] = current_prices[asset]
#                self.asset_log[asset]["cashflow"].loc[pd.to_datetime(date), amount_str] = self.portfolio.loc[asset, amount_str]
    
    
# Pandas to JSON: j = df.to_json()
# Dictionary to JSON: 
# import json
# j = json.dumps(dict)
    

if __name__ == "__main__":
    
    name = "John Smith"
    portfolio_id = "AAA"
    date = "2020-06-12"
    account = {name: [Reporting(date, portfolio_id, 10000, "EUR")]}

    asset_info1 = {"date": "2020-06-19",
                  "bank": "Bper",
                  "isin": "IT0000388907",
                  "title": "Arca Azioni Italia",
                  "price": 20.4554,
                  "nav": 20.4554,
                  "commission": 0,
                  "currency": "EUR",
                  "maturity": ""}
    
    asset_info2 = {"date": "2020-06-22",
                  "bank": "Bper",
                  "isin": "IT0000388907",
                  "title": "Arca Azioni Italia",
                  "price": 20.4554,
                  "nav": 20.4554,
                  "commission": 0,
                  "currency": "EUR",
                  "maturity": ""}
    
    asset_info3 = {"date": "2020-01-01",
                  "bank": "Bper",
                  "isin": "IT0005104473",
                  "title": "CctEu 15Giu22 TV",
                  "price": 20.4554,
                  "nav": 20.4554,
                  "commission": 0,
                  "currency": "EUR",
                  "maturity": ""}
    
    interest_info = {"date": "2020-06-20",
                     "isin": "IT0005104473",
                     "title": "CctEu 15Giu22 TV",
                     "quantity": 1000,
                     "amount": 450,
                     "currency": "EUR"}
    
    account[name][0].buy(asset_info3, 10)
    account[name][0].deposit("2020-06-14", 5000)
    account[name][0].deposit("2020-06-14", 5000)
    account[name][0].withdraw("2020-06-17", 5000)
    account[name][0].buy(asset_info1, 10)
    account[name][0].sell(asset_info2, 50)
    account[name][0].interest(interest_info)    

    
    
