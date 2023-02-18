from pathlib import Path
from typing import Dict
import json
import scrapy
import psycopg2
import datetime
from collections import namedtuple
import os
import time


COUNT = os.environ["COUNT"]
DB_TABLE_NAME = os.environ["DB_TABLE_NAME"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.environ["POSTGRES_PORT"]


FlatData = namedtuple('FlatData', ('title', 'link', 'image_link'))


def get_cursor(tries=0):
    try:
        connection = psycopg2.connect(database=POSTGRES_DB, user=POSTGRES_USER, password=POSTGRES_PASSWORD, host=POSTGRES_HOST, port=POSTGRES_PORT)
    except psycopg2.OperationalError as e:
        if tries < 10:
            time.sleep(1)
            return get_cursor(tries + 1)

        raise e

    return connection, connection.cursor()


def prepare_table(cursor, connection):
    """
    If table with name DB_TABLE_NAME doesnt exist, create it.
    """

    cursor.execute("""SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'""")
    existing_table_names = [x[0] for x in cursor.fetchall()]

    if DB_TABLE_NAME not in existing_table_names:
        cursor.execute(f" \
            CREATE TABLE {DB_TABLE_NAME} (\
            RecordID int, \
            Timestamp timestamp, \
            Title text, \
            URL text, \
            Image bytea \
        );")
        connection.commit()


def process_flat_data(response: Dict):
    flats = response["_embedded"]["estates"]

    flat_data = []

    for flat in flats:
        title = flat["name"]
        rooms_str = title.split(" ")[3]
        place_str = flat["seo"]["locality"]
        sreality_id = flat["hash_id"]
        link = f"https://www.sreality.cz/en/detail/sale/flat/{rooms_str}/{place_str}/{sreality_id}"
        image_link = flat["_links"]["images"][0]["href"]
        flat_data.append(FlatData(title, link, image_link))

    return flat_data


class FlatsSpider(scrapy.Spider):
    name = "flats"

    def __init__(self, *args, **kwargs):
        self.connection, self.cursor = get_cursor()
        prepare_table(self.cursor, self.connection)
        super().__init__(*args, **kwargs)

    def start_requests(self):
        urls = [
            f"https://www.sreality.cz/api/en/v2/estates?category_main_cb=1&category_type_cb=1&per_page={COUNT}"
        ]
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        page = response.url.split("/")[-2]
        flat_data = process_flat_data(json.loads(response.body))
        timestamp = datetime.datetime.now()

        for single_flat_data in flat_data:
            yield scrapy.Request(url=single_flat_data.image_link, callback=self.parse_image, meta={"flat_data": single_flat_data, "timestamp": timestamp})

    def parse_image(self, response):
        flat_data = response.meta.get("flat_data")
        timestamp = response.meta.get("timestamp")
        image_data = response.body

        self.cursor.execute(f"SELECT COUNT (*) FROM {DB_TABLE_NAME}")
        db_size = self.cursor.fetchone()[0]

        self.cursor.execute(f"INSERT INTO {DB_TABLE_NAME} (RecordID, Timestamp, Title, URL, Image) VALUES (%s, %s, %s, %s, %s)", (db_size, timestamp, flat_data.title, flat_data.link, image_data))
        self.connection.commit()


if __name__ == "__main__":
    downloaded_path = "/home/beda/luxonis/flats_downloader/flats-json-500-v2.json"
    with open(downloaded_path, "r") as input_file:
        file_content = json.loads(input_file.read())
    
        process_response(file_content)
