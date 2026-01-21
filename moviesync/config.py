import logging

import yaml

logger = logging.getLogger(__name__)


class Config:
    def load():
        with open("config.yml", "r") as yml_file:
            data = yaml.load(yml_file, Loader=yaml.FullLoader)

        return data
