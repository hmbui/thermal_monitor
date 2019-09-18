import os
from enum import Enum
import json
import time

import logging
from logging.handlers import RotatingFileHandler

from defaults import METADATA_FILE_NAME, MAX_FILE_SIZE_BYTES, MAX_FILE_COUNT


class DataType(Enum):
    UNKNOWN = -1
    INFO = 0
    WARNING = 1
    ERROR = 2
    EXCEPTION = 3


METADATA = {
    "__data_collection_version": "1.0.0",

    "collection_start": -1,
    "collection_end": -1
}


class DataLogger:
    """
    Responsible for writing metric data collected into a rotating set of files. Each set of files contains:

    1. A metadata file, in the JSON format
    2. A text data file
    """
    def __init__(self, data_file_dir, max_file_size=MAX_FILE_SIZE_BYTES, max_file_count=MAX_FILE_COUNT):
        """
        Set up the rotating data file mechanism.

        :param data_file_dir: The path to create the root data file directory
        :type: str
        :param max_file_size: The maximum size, in bytes, to write to a data file before starting writing to a new file
        :type: int
        :param max_file_count: The maximum number of data files to write before starting to go back to the first
            data file to write the latest data (thus removing the oldest data file)
        :type: int
        """
        self._data_dir_path = os.path.join(data_file_dir)
        os.makedirs(self._data_dir_path, exist_ok=True)

        self._max_file_size = max_file_size
        self._max_file_count = max_file_count

        self._formatter = logging.Formatter("%(message)s")
        self._rotating_file_handler = RotatingFileHandler(os.path.join(
            self._data_dir_path, "cpu_temperatures"), maxBytes=self._max_file_size, backupCount=self._max_file_count)
        self._rotating_file_handler.setFormatter(self._formatter)

        self._console_handler = logging.StreamHandler()
        self._console_handler.setFormatter(self._formatter)

        self._logger = logging.getLogger()
        self._logger.setLevel(logging.INFO)
        self._logger.addHandler(self._rotating_file_handler)
        self._logger.addHandler(self._console_handler)

        self._metadata = METADATA

    def set_logging_level(self, logging_level):
        self._logger.setLevel(logging_level)

    def start(self):
        """
        Start the data collection. This will add the start timestamp into the metadata, and
        update the metadata file.
        """
        self._metadata["collection_start"] = time.time()
        self._write_metadata()

    def _write_metadata(self):
        """
        Create a new metadata file with the latest available metadata written to that file.
        """
        with open(os.path.join(self._data_dir_path, METADATA_FILE_NAME), 'w') as metadata_file:
            json.dump(self._metadata, metadata_file, indent=4, separators=(',', ':'))

    def write(self, data, data_type=DataType.INFO):
        """
        Write data into a data file. This uses the logger object of Python. For warnings, errors, and exceptions, the
        writer will switch to the corresponding logging method of the Python logger.

        :param data: The data to write to a file
        :type: str
        :param data_type: The type of data, i.e. the data INFO, or a WARNING, or an ERROR, or an EXCEPTION
        :type: Enum
        """
        switcher = {
            DataType.INFO: self._logger.info,
            DataType.WARNING: self._logger.warning,
            DataType.ERROR: self._logger.error,
            DataType.EXCEPTION: self._logger.exception
        }

        handler = switcher.get(data_type, None)
        handler(data) if handler else self._logger.exception(
            "Unknown data type '{0}'. Make sure you provide one of the supported data type values: {1}".format(
                data_type, [{i.name: i.value for i in DataType}]))

    def reset_file_handler(self, data_dir_path, max_file_size=None, max_file_count=None):
        """
        Change the file handler so that the next data to write will be directed into a different data file, in a
        different location in the data file hierarchy.

        :param data_dir_path: The new path to the root directory. This must end with the root directory name
        :type: str
        :param max_file_size: The maximum size, in bytes, for each data file before a new data file is created. If None,
            use the default data file size
        :type: int
        :param max_file_count: The maximum number of data files to write before starting to go back to the first
            data file to write the latest data (thus removing the oldest data file). If None, use the default data file
            count
        :type: int
        """
        self._rotating_file_handler = RotatingFileHandler(os.path.join(data_dir_path, "cpu_temperatures"),
                                                          maxBytes=max_file_size if max_file_size else
                                                          self._max_file_size,
                                                          backupCount=max_file_count if max_file_count else
                                                          self._max_file_count)

    def end(self):
        """
        Stop the data collection for the selected chart. This updates the "collection_end" timestamp, and update the
        metadata file.
        """
        self._metadata["collection_end"] = time.time()
        self._write_metadata()
