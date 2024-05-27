import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import boto3

logger = logging.getLogger("s3logger")


def print_directory_rotation_stats(filename, rotated_files, s3_path):
    """Logging rotation stats to ensure that the backup count and path are correct
    on each rotation cycle.

    :param filename:
    :param rotated_files:
    :param s3_path:
    :return:
    """
    logger.info(f"Log file stats")
    logger.info(f"Current file: {filename}")
    logger.info(f"Len of rotated files: {len(rotated_files)}")
    logger.info(f"Rotated files list: {rotated_files}")
    logger.info(f"S3 path: {s3_path}")


class S3TimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, bucket_name, aws_access_key_id, aws_secret_access_key, when="m", interval=1, backupCount=5):
        super().__init__(filename, when, interval, backupCount)
        self.bucket_name = bucket_name
        self.s3_client = boto3.client("s3", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

    def doRollover(self):
        # Perform the log rotation
        super().doRollover()
        current_log_path = self.baseFilename
        log_dir, log_filename = os.path.split(current_log_path)
        rotated_files = [f for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f)) and f.startswith(log_filename)]

        rotated_files.sort(key=lambda f: os.path.getmtime(os.path.join(log_dir, f)), reverse=True)
        s3_path = ""
        if rotated_files:
            # The most recently modified file that matches the original log filename pattern should be the rotated file
            rotated_file_path = os.path.join(log_dir, rotated_files[1])
            s3_path = self.upload_file_to_s3(rotated_file_path)

        print_directory_rotation_stats(log_filename, rotated_files, s3_path)

    def upload_file_to_s3(self, file_path):
        file_name = os.path.basename(file_path)
        now = datetime.now()
        formatted_today_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H-%M-%S")

        # remove the datetime from the log rotation
        adjusted_s3_key_name = ".".join(file_name.split(".")[:2])
        s3_path = f"logs/conference=ckc/app={os.getenv('APP_NAME')}/date={formatted_today_date}/{current_time}-{adjusted_s3_key_name}"
        try:
            response = self.s3_client.upload_file(file_path, self.bucket_name, s3_path)
            return s3_path
        except Exception as e:
            logger.error(f"Failed to upload {file_path} to S3: {e}")
