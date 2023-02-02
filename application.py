from startup import ServiceManager


if __name__ == "__main__":
    ServiceManager.initialize_logger()
    ServiceManager.initialize_config()
    ServiceManager.initialize_exchange_service()

    input()
