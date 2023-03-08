# AlgoTrader



### TODO
- [ ] Add more exchanges
- [X] Normalize data coming from exchanges
  - [X] When you make call to exchange, you get data in different formats, find the common structure
  - [X] Normalize data to common structure
- [ ] Implement global config mechanism (link to config file)

#### Refactoring
- [ ] Separate exchange specific methods into the abstract class and leave base class as an interface (with correct naming)

#### Feature
- [ ] Add scan on historical values and retrieve missing ranges
- [ ] Backfill those ranges
- [ ] Create correct program flow
- [ ] Implement decision maker algorithm
  - [ ] There could be several models, which are many. Implement those
  - [ ] Create scoring mechanism
  - [ ] Create scoring feedback mechanism by the success rates of the trades
- [ ] Create or use a library for binance client
  - [ ] Wrap this library to provide more functionality
  - [ ] Implement mock tester
- [ ] Implement archiving mechanism
- [ ] Implement technical indicators
  - [ ] There should be at least 5 indicators
    - [ ] SMA
    - [ ] EMA
    - [ ] RSI
    - [ ] VWAP
    - [ ] MACD
  - [ ] Search for any other method that can be useful for prediction of price
  - 