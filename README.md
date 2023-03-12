# AlgoTrader



### TODO
- [ ] Add more exchanges
- [X] Normalize data coming from exchanges
  - [X] When you make call to exchange, you get data in different formats, find the common structure
  - [X] Normalize data to common structure
- [ ] Implement global config mechanism (link to config file)

#### Refactoring
- [X] Separate exchange specific methods into the abstract class and leave base class as an interface (with correct naming)
- [ ] Move all initialization process to a method from constructor NOTE: DON'T DO THIS, IT'S NOT A GOOD PRACTICE

#### Feature
- [X] Add scan on historical values and retrieve missing ranges
- [X] Backfill those ranges
- [ ] Create correct program flow
- [ ] Implement decision maker algorithm
  - [ ] There could be several models, which are many. Implement those
    - [ ] Decision Maker
      - [ ] There should be at least 5 models
        - [ ] ARIMA
        - [ ] LSTM
        - [ ] GPR
        - [ ] Random Forest
        - [ ] XGBoost
  - [ ] Create scoring mechanism
  - [ ] Create scoring feedback mechanism by the success rates of the trades
- [ ] Create or use a library for binance client
  - [ ] Wrap this library to provide more functionality
  - [ ] Implement mock tester
- [ ] Implement archiving mechanism
- [ ] Implement technical indicators
  - [ ] Implement Jobs mechanism
    - [ ] Technical Indicators
        - [ ] There should be at least 5 indicators
          - [ ] SMA
          - [ ] EMA
          - [ ] RSI
          - [ ] VWAP
          - [ ] MACD
    - [ ] Create Dependency mechanism - The point is to avoid calculating the same thing twice
      - [ ] Technical Indicators
        - [ ] SMA
          - [ ] Depends on: Close
        - [ ] EMA
          - [ ] Depends on: Close
        - [ ] RSI
          - [ ] Depends on: Close
        - [ ] VWAP
          - [ ] Depends on: Close, Volume
        - [ ] MACD
          - [ ] Depends on: Close
          - [ ] Depends on: EMA
  - [ ] Search for any other method that can be useful for prediction of price
  - [ ] Design an UI
    - [ ] Profit and loss analysis
    - [ ] Current price, graph, indicators and position
    - [ ] History of trades
    - [ ] Custom buy/sell orders over the current position
    - [ ] Custom buy/sell orders over the current price
    - [ ] Login Page (possibly keycloak)
    
#### Bug
- [ ] It should make roughly 2900 calls for btcusdt when it's backfilling, but it makes 5900 calls. Find the reason and fix it


### OpenAI Suggestions

Sure, here are some commonly used models in finance and stock trading:

1. Autoregressive Integrated Moving Average (ARIMA): This is a statistical model that uses time series data to make predictions. It has been widely used in finance for predicting stock prices, exchange rates, and other economic indicators. ARIMA models are good for predicting trends and patterns in data over time, but may struggle with sudden changes in data or noisy data.
2. Long Short-Term Memory (LSTM): This is a type of Recurrent Neural Network (RNN) that is good for modeling sequences of data. LSTMs can learn long-term dependencies in time series data and can be used for stock price prediction, portfolio optimization, and risk management. However, LSTMs may require a lot of data and computational resources to train.
3. Gaussian Process Regression (GPR): This is a non-parametric model that can be used for time series prediction, volatility modeling, and option pricing. GPR models can capture complex patterns in data and can be more flexible than parametric models like ARIMA. However, they may also be computationally expensive and may require careful tuning of hyperparameters.
4. Random Forests: This is a popular machine learning algorithm that can be used for stock price prediction and portfolio optimization. Random forests are good at handling noisy data and can capture non-linear relationships between features and target variables. However, they may struggle with overfitting if the model is too complex.
5. XGBoost: This is a gradient boosting algorithm that is widely used in finance and stock trading. It is known for its accuracy and speed, and has been used for portfolio optimization, risk management, and fraud detection. XGBoost models can handle missing data and can capture complex patterns in data, but may require careful tuning of hyperparameters and regularization to avoid overfitting.

It's important to note that these models should be used as tools to aid decision-making, and not as a substitute for expert knowledge and judgment. Financial markets can be unpredictable and subject to sudden changes, so it's important to carefully evaluate the risks and limitations of any model before using it for trading decisions.

The choice of model(s) to use in a trading bot will depend on the specific trading strategy and the available data. In general, it may be beneficial to use a combination of multiple models with some scoring to leverage the strengths of each model and reduce the risk of relying on a single model.

For example, one possible approach would be to use a time-series forecasting model like ARIMA or LSTM to predict future prices, and then use a machine learning model like Random Forest or XGBoost to classify whether to buy, hold, or sell based on the predicted prices and other features like volume, news sentiment, and technical indicators.

Another possible approach would be to use a Gaussian Process Regression (GPR) model to model the underlying trend and volatility of the stock, and then use a reinforcement learning algorithm like Deep Q-Learning to learn the optimal trading strategy based on the predicted trend and volatility.

It's also important to note that the performance of a trading bot will depend not only on the choice of model(s) but also on factors like the quality and timeliness of the data, the accuracy of the trading strategy, and the execution speed of the bot.

In practice, it may be beneficial to start with a simple trading strategy and a basic model like ARIMA or Random Forest, and then gradually improve the strategy and model as more data and resources become available. It's also important to regularly evaluate the performance of the bot and adjust the strategy and model as needed to adapt to changing market conditions.