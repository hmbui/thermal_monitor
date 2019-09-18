import os
try:
    from os import errno
except ImportError:
    # For Python 3.7
    import errno
import sys
import time
import datetime
import json
import argparse

from data_logger import DataLogger, DataType


# Store the log file to "./logs/"
try:
    os.makedirs("logs")
except os.error as err:
    # It's OK if the log directory exists. This is to be compatible with Python 2.7
    if err.errno != errno.EEXIST:
        raise err

data_logger = DataLogger("logs", max_file_size=4000, max_file_count=10)


def _parse_configs(config_file_path):
    """
    Parse the configuration file.

    :param config_file_path: The path to the configuration file (including the filename)
    :type: str
    :return: The configuration data
    :rtype: dict
    """
    with open(config_file_path, 'r') as config_file:
        configs = json.load(config_file)
    return configs


def _parse_arguments():
    """
    Parse the command arguments.

    :return: The command arguments as a dictionary
    :rtype: dict
    """
    parser = argparse.ArgumentParser(
        description="A tool to check whether SSH tunnels are opened for user-provided reverse-tunnel ports.")

    parser.add_argument(
        '--log-level',
        help='Configure level of log display',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO'
    )

    parser.add_argument("--config-file",
                        help="The path to the configuration file")

    args, extra_args = parser.parse_known_args()
    return args, extra_args


def _count_down_sleep_status(sleep_secs):
    """
    Display a countdown of the remaining sleep seconds.

    :param sleep_secs: The number of seconds for sleep
    :type: int
    """
    for i in range(sleep_secs, 0, -1):
        sys.stdout.write("\rSleeping for {0} seconds...".format(i))
        sys.stdout.flush()
        time.sleep(1)
        sys.stdout.flush()


def collect_thermal_readings(delay_sec, attempts):
    """
    Execute repeated thermal readings with delays

    :param delay_sec: The number of seconds to delay before next attempt
    :type: int
    :param attempts: The number of attempts if there is an exception thrown during the test
    :type: int
    :raise: IOError
    """
    def read_thermal_data():
        file = open("/sys/class/thermal/thermal_zone0/temp", 'r')
        milli_celsius = int(file.read().strip())
        whole_celsius = milli_celsius // 1000
        decimal_celsius = milli_celsius - whole_celsius * 1000

        whole_fahrenheit = whole_celsius * 1.8 + 32
        decimal_fahrenheit = decimal_celsius * 1.8 + 32

        c_reading = str(round(milli_celsius / 1000, 3)) + "\xb0C"
        f_reading = str(round(whole_fahrenheit + decimal_fahrenheit / 1000, 3)) + "\xb0F"

        return c_reading, f_reading

    try:
        attempt_count = 0
        while attempt_count < attempts:
            attempt_count += 1

            c_reading, f_reading = read_thermal_data()

            data_logger.write('\n' + c_reading + '\n' + f_reading)

            _count_down_sleep_status(delay_sec)
    except IOError:
        data_logger.write('\r')
        data_logger.write("Cannot find thermal data.\n".format(), DataType.ERROR)


def main():
    args, extra_args = _parse_arguments()

    if args.log_level:
        # The user can set the log level to lower or higher than INFO (the default)
        data_logger.set_logging_level(args.log_level)

    if not args.config_file:
        config_file_path = os.path.join("configs", "config.json")
    else:
        # The user can store the "config.json" file in a different directory
        config_file_path = os.path.join(os.path.expandvars(os.path.expanduser(args.config_file)), "config.json")

    configs = _parse_configs(config_file_path)

    delay_sec = configs["delay_sec"]
    attempts = configs["attempts"]

    data_logger.start()

    data_logger.write('\n')
    data_logger.write('=' * 30)
    data_logger.write(datetime.datetime.now())
    data_logger.write('-' * 30)

    collect_thermal_readings(delay_sec, attempts)

    data_logger.write('\n')
    data_logger.write('-' * 30)
    data_logger.write(datetime.datetime.now())
    data_logger.write('=' * 30)

    data_logger.end()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        data_logger.write(type(error))
        data_logger.write("Encountered unknown exception: {}".format(error), DataType.ERROR)
