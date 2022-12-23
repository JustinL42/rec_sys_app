import configparser
import os

config_parser = configparser.ConfigParser()
config_dir = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "config",
)
config_files = [os.path.join(config_dir, f) for f in os.listdir(config_dir)]
config_parser.read(config_files)
env = os.environ.get("ENV", "DEFAULT")
config = config_parser[env]

for key, value in config.items():
    print(f"{key}={value}")
