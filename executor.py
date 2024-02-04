from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment

import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

ALPACA_CREDS = {
    'API_KEY': API_KEY,
    'API_SECRET': API_SECRET,
    'PAPER': True
}

class MLTrader(Strategy):

    # runs once
    def initialize(self, symbol:str="SPY", cash_at_risk:float=.15):
        self.symbol = symbol
        self.sleep_time = "2H" # Time the program will pause between iterations for the on_trading_iteration function
        self.last_trade = None
        self.cash_at_risk = cash_at_risk # The percentage of cash to risk on each trade
        self.api = REST(key_id=API_KEY, secret_key=API_SECRET, base_url='https://paper-api.alpaca.markets')
    
    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)

        # Formula used: Position Size = (Total Portfolio Value * Risk Percentage) / (Stop Loss Distance)
        position_size = round((cash * self.cash_at_risk) / last_price, 0)

        return cash, last_price, position_size

    def get_dates(self):
        today = self.get_datetime()
        three_days_ago = today - Timedelta(days=3)

        return three_days_ago.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    def get_sentiment(self):
        # self.api.get_news(symbol=self.symbol, start=datetime.now() - timedelta(days=1), end=datetime.now()
        today, three_days_ago = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, 
                                 start=today,
                                 end=three_days_ago)
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)

        return probability, sentiment

    # iterates every time we get new data
    def on_trading_iteration(self):

        cash, last_price, position_size = self.position_sizing()
        probability, sentiment = self.get_sentiment()
        
        take_profit_price_long = .2
        stop_loss_price_long = .05
        
        if cash > last_price:

            # long
            if sentiment == 'positive' and probability > .9:
                if self.last_trade == 'sell':
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    position_size,
                    "buy",
                    type="bracket",
                    take_profit_price=last_price * (1 + take_profit_price_long),
                    stop_loss_price=last_price * (1 - stop_loss_price_long)
                )

                self.submit_order(order)
                self.last_trade = 'buy'
            
            # short
            elif sentiment == 'negative' and probability > .9:
                if self.last_trade == 'buy':
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    position_size,
                    "sell",
                    type="bracket",
                    take_profit_price=last_price * (1 - take_profit_price_long),
                    stop_loss_price=last_price * (1 + stop_loss_price_long)
                )

                self.submit_order(order)
                self.last_trade = 'sell'

broker = Alpaca(ALPACA_CREDS)

strategy = MLTrader(name='mlstrat',
                    broker=broker,
                    parameters={"symbol": 'SPY',
                                "cash_at_risk":.5
                                }
                    )

start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 2, 1)

# To deploy this live

# Comment this section
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol": 'SPY',
                "cash_at_risk":.5
                }
)

# Uncomment this section
# trader = Trader()
# trader.add_strategy(strategy)
# trader.run_all()