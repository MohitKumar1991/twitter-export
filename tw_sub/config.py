import os
import logging

env = os.environ.get("ENV", "dev")

class Config:
    """
    Base Configuration
    """

    # CHANGE SECRET_KEY!! I would use sha256 to generate one and set this as an environment variable
    # Exmaple to retrieve env variable `SECRET_KEY`: os.environ.get("SECRET_KEY")
    secret_key = "testkey"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_FILE = "api.log"  # where logs are outputted to


class DevelopmentConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///./common.db'
    SQLALCHEMY_CONNECT_ARGS = {"check_same_thread": False }
    TWITTER_USERNAME = 'balajis'
    DEBUG = True


class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",  "postgresql://testusr:password@127.0.0.1:5432/testdb"
    )  # you may do the same as the development config but this currently gets the database URL from an env variable
    SQLALCHEMY_CONNECT_ARGS = { }
    HTTP_USERNAME = os.environ.get(
        "BASIC_USERNAME", "noob"
    )
    HTTP_PASSWORD = os.environ.get(
        "BASIC_PASSWORD", "nommr"
    )
    TWITTER_USERNAME = os.environ.get(
        "TWITTER_USERNAME", ""
    )
    DEBUG = False

if env == 'dev':
    config = DevelopmentConfig
elif env == 'prod':
    config = ProductionConfig
else:
    raise Exception('Invalid Environment')

logging.debug(f"CONFIG LOADED {env} {config} {config.SQLALCHEMY_DATABASE_URI} {config.DEBUG}")


