
import pandas as pd
import numpy as np


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
nav_str = "NAV"
fee_str = "Fee"
commission_str = "Commission"
cost_str = "Cost"
maturity_str = "Maturity"
amount_str = "Value Gross"
amount_net_str = "Value Net"
weight_str = "Weight"
cash_str = "Cash"
coupon_str = "Coupon"
pnl_str = "PnL"
irr_str = "IRR"
annualised_return_str = "Annualised Return"


class Reporting:
    
    def __init__(self, date, portfolio_id, initial_balance, currency):
        self.balance = initial_balance
        self.currency = currency
        self.portfolio_id = portfolio_id
        self.portfolio = pd.DataFrame([], columns=[isin_str, currency_str, maturity_str, quantity_str, price_str, rate_str, amount_str, amount_net_str, weight_str])
        self.portfolio.index.name = title_str
        self.portfolio.loc[cash_str] = ["", currency, "", initial_balance, 1,  1, initial_balance, initial_balance, 1]
        self.current_account = pd.DataFrame([[pd.to_datetime(date), deposit_str, initial_balance, initial_balance, deposit_str]],
                                   columns=[date_str, operation_str, cash_flow_str, balance_str, record_str])
        self.buysell = pd.DataFrame([], columns=[portfolio_str, bank_str, date_str, isin_str, currency_str, rate_str, title_str, operation_str, quantity_str, price_str, nav_str, fee_str, commission_str, cost_str])
        self.asset_log = {}
    
    def __normalise(self):
        self.portfolio.loc[cash_str, amount_str] = self.balance
        self.portfolio.loc[cash_str, amount_net_str] = self.balance
        self.portfolio[weight_str] = self.portfolio[amount_net_str] / self.portfolio[amount_net_str].sum()
        
    def __reorder(self):
        index = [x for x in self.portfolio.index if x!=cash_str]
        index += [cash_str]
        self.portfolio = self.portfolio.reindex(index=index)
    
    def __update_cash(self):
        self.portfolio.loc[cash_str, quantity_str] = self.balance
        self.portfolio.loc[cash_str, amount_str] = self.balance
        self.portfolio.loc[cash_str, amount_net_str] = self.balance
    
    def __clean(self):
        self.portfolio = self.portfolio[self.portfolio[amount_net_str] > 0.01]
        self.portfolio.loc[cash_str, maturity_str] = ""
        self.portfolio.loc[cash_str, quantity_str] = 1
        self.portfolio.loc[cash_str, price_str] = 1
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
    
    def buy(self, asset_info, quantity, exchange_rate=1):
        amount_ = quantity * asset_info["price"]
        amount = amount_ + asset_info["fee"] + amount_ * asset_info["commission"]
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
                       rate_str: exchange_rate,
                       title_str: asset_info["title"],
                       operation_str: buy_str,
                       quantity_str: quantity,
                       price_str: asset_info["price"],
                       nav_str: asset_info["nav"],
                       fee_str: asset_info["fee"],
                       commission_str: asset_info["commission"],
                       cost_str: amount}
        self.buysell.loc[len(self.buysell)] = buysell_enrty
        if asset_info["title"] not in self.portfolio.index:
            self.portfolio.loc[asset_info["title"]] = [asset_info["isin"], asset_info["currency"], asset_info["maturity"], quantity, asset_info["price"], exchange_rate, amount_, amount, 0]
        else:
            self.portfolio.loc[asset_info["title"], quantity_str] += quantity
            self.portfolio.loc[asset_info["title"], price_str] = asset_info["price"]
            self.portfolio.loc[asset_info["title"], rate_str] = exchange_rate
            self.portfolio.loc[asset_info["title"], amount_str] += amount
            self.portfolio.loc[asset_info["title"], amount_net_str] += amount_
        self.__update_cash()
        self.__normalise()
        self.__reorder()
        self.__clean()
        if asset_info["title"] not in self.asset_log:
            self.asset_log[asset_info["title"]] = {"isin": asset_info["isin"], "currency": asset_info["currency"],
                          "cashflow": pd.DataFrame([], columns=[asset_info["title"]])}
        self.asset_log[asset_info["title"]]["cashflow"].loc[pd.to_datetime(asset_info["date"])] = -amount
            
        
    def sell(self, asset_info, quantity, exchange_rate=1):
        if asset_info["title"] not in self.portfolio.index: return
        quantity = min(quantity, self.portfolio.loc[asset_info["title"], quantity_str])
        amount_ = quantity * asset_info["price"]
        amount = amount_ + asset_info["fee"] + amount_ * asset_info["commission"]
        if amount < 0.01: return
        self.balance += amount
        record_data_str = sell_str + ": " + asset_info["title"] + " ISIN: " + asset_info["isin"]
        self.current_account.loc[len(self.current_account)] = [pd.to_datetime(asset_info["date"]), sell_str, amount, self.balance, record_data_str]
        buysell_enrty = {portfolio_str: self.portfolio_id,
                       bank_str: asset_info["bank"],
                       date_str: pd.to_datetime(asset_info["date"]),
                       isin_str: asset_info["isin"],
                       currency_str: asset_info["currency"],
                       rate_str: exchange_rate,
                       title_str: asset_info["title"],
                       operation_str: sell_str,
                       quantity_str: quantity,
                       price_str: asset_info["price"],
                       nav_str: asset_info["nav"],
                       fee_str: asset_info["fee"],
                       commission_str: asset_info["commission"],
                       cost_str: amount}
        self.buysell.loc[len(self.buysell)] = buysell_enrty
        self.portfolio.loc[asset_info["title"], quantity_str] -= quantity
        self.portfolio.loc[asset_info["title"], price_str] = asset_info["price"]
        self.portfolio.loc[asset_info["title"], rate_str] = exchange_rate
        self.portfolio.loc[asset_info["title"], amount_str] -= amount_
        self.portfolio.loc[asset_info["title"], amount_net_str] -= amount_
        self.portfolio.loc[cash_str, quantity_str] = self.balance
        self.portfolio.loc[cash_str, amount_str] = self.balance
        self.portfolio.loc[cash_str, amount_net_str] = self.balance
        self.__update_cash()
        self.__normalise()
        self.__reorder()
        self.__clean()
        self.asset_log[asset_info["title"]]["cashflow"].loc[pd.to_datetime(asset_info["date"])] = amount
        
    def interest(self, interest_info):
        self.balance += interest_info["amount"]
        interest_str = "Dividend / Coupon"
        record_data_str = "Title: " + interest_info["isin"] + " " + interest_info["currency"] + " Qty: " + str(interest_info["quantity"]) + " (" + interest_info["title"] + ")"
        self.current_account.loc[len(self.current_account)] = [pd.to_datetime(interest_info["date"]), interest_str, interest_info["amount"], self.balance, record_data_str]
        self.__normalise()        
        if interest_info["title"] not in self.asset_log:
            print ("IF CHECK")
            self.asset_log[interest_info["title"]] = {"isin": interest_info["isin"], "currency": interest_info["currency"],
                          "cashflow": pd.DataFrame([], columns=[interest_info["title"]])}
        self.asset_log[interest_info["title"]]["cashflow"].loc[pd.to_datetime(interest_info["date"])] = interest_info["amount"]        
        self.__update_cash()
        self.__normalise()
    
    def __portfolio_total(self):
        portfolio_total = {amount_str: self.portfolio[amount_str].sum(), 
                           amount_net_str: self.portfolio[amount_net_str].sum(), 
                           weight_str: self.portfolio[weight_str].sum()}
        return portfolio_total
    
    def positions(self):
        return self.portfolio, self.__portfolio_total()
        
    def returns(self):
        df = pd.DataFrame([], columns=[isin_str, currency_str, coupon_str, pnl_str, irr_str, annualised_return_str], index=self.asset_log.keys())
        resampled_list = []
        ii_list = []
        for asset in self.asset_log:
            df.loc[asset, isin_str] = self.asset_log[asset]["isin"]
            df.loc[asset, currency_str] = self.asset_log[asset]["currency"]
            df.loc[asset, coupon_str] = 0
            cashflow = self.asset_log[asset]["cashflow"]
            ii = cashflow.iloc[0, 0]
            ii_list.append(ii)
            if len(cashflow) > 1:
                resampled = cashflow.iloc[1:].resample("y").sum()
                resampled_list.append(resampled)
                irr = np.irr([ii] + [x[0] for x in resampled.values])
                df.loc[asset, irr_str] = irr
                df.loc[asset, pnl_str] = cashflow.iloc[:, 0].sum()
                df.loc[asset, annualised_return_str] = cashflow.iloc[:, 0].sum() / -cashflow.iloc[0, 0] / (cashflow.index[-1] - cashflow.index[0]).days * 252 
            else:
                df.loc[asset, irr_str] = 0
                df.loc[asset, pnl_str] = 0
                df.loc[asset, annualised_return_str] = 0
            df.loc[asset, coupon_str] = 0
        if resampled_list != []:
            resampled_portfolio = pd.concat(resampled_list, axis=1).sum(axis=1)
            irr_portfolio = np.irr([np.sum(ii_list)] + [x for x in resampled_portfolio.values])
            pnl_portfolio = df[pnl_str].sum()
            ar_portfolio = resampled_portfolio.mean(axis=0) / np.sum(ii_list) - 1
        df_total = {coupon_str: df[coupon_str].sum(),
                    pnl_str: pnl_portfolio,
                    irr_str: irr_portfolio,
                    annualised_return_str: ar_portfolio}
        return df, df_total
 

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
                  "fee": 0,
                  "commission": 0,
                  "currency": "EUR",
                  "maturity": ""}
    
    asset_info2 = {"date": "2020-06-22",
                  "bank": "Bper",
                  "isin": "IT0000388907",
                  "title": "Arca Azioni Italia",
                  "price": 20.4554,
                  "nav": 20.4554,
                  "fee": 0,
                  "commission": 0,
                  "currency": "EUR",
                  "maturity": ""}
    
    asset_info3 = {"date": "2020-01-01",
                  "bank": "Bper",
                  "isin": "IT0005104473",
                  "title": "CctEu 15Giu22 TV",
                  "price": 20.4554,
                  "nav": 20.4554,
                  "fee": 0,
                  "commission": 0,
                  "currency": "EUR",
                  "maturity": ""}
    
    interest_info = {"date": "2020-06-20",
                     "isin": "IT0005104473",
                     "title": "CctEu 15Giu22 TV",
                     "quantity": 1000,
                     "amount": 450,
                     "currency": "EUR"}
    
    account[name][0].buy(asset_info3, 10, 1)
    account[name][0].deposit("2020-06-14", 5000)
    account[name][0].deposit("2020-06-14", 5000)
    account[name][0].withdraw("2020-06-17", 5000)
    account[name][0].buy(asset_info1, 10, 1)
    account[name][0].sell(asset_info2, 50, 1)
    account[name][0].interest(interest_info)    
    rets = account[name][0].returns()

    
    
    
