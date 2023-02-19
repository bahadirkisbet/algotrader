from common_models.exchange_type import ExchangeType
from data_center.data_center import DataCenter
from data_provider.exchange_collection.exchange_factory import ExchangeFactory
from startup import ServiceManager


if __name__ == "__main__":
    ServiceManager.initialize_logger()
    ServiceManager.initialize_config()
    config = ServiceManager.get_service("config")
    exchange_name = config["EXCHANGE"]["exchange_code"]
    exchange = ExchangeFactory.create(exchange_name, ExchangeType.SPOT)
    ServiceManager.add_service("exchange", exchange)

    dataCenter = DataCenter()
    dataCenter.start()

    input()
