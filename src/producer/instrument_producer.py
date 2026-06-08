import uuid
import requests
import math
import json
import time
from kafka.errors import NoBrokersAvailable
from kafka import KafkaProducer
from src.producer.credentials import get_user_key, get_api_key

print("--------------------------------------------------")
print(">> Extracting instrument id for symbols from eToro...")
print("--------------------------------------------------")

#Get relevant variables for API
url = "https://public-api.etoro.com/api/v1/instruments/discover"
headers = {
    "x-request-id": str(uuid.uuid4()),
    "x-api-key": get_api_key(),
    "x-user-key": get_user_key(),
}

#Define producer
def create_producer():
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers = ["kafka:9092"],
                value_serializer = lambda x: json.dumps(x).encode("utf-8")
            )
            return producer
        except NoBrokersAvailable:
            print("Waiting for kafka...")
            time.sleep(3)

producer = create_producer()

#Instrument retrieval from API
def fetch_instruments(page_size = 2000):
    '''
    Purpose:
    - Iterates through instrument pages and returns instrument id's and relevant details relating to these from API

    Args:
    - page_size (DEFAULT = 2000) - the number of instruments to display on each page
    '''
    try:
        #get first page to identify total pages to iterate through
        response = requests.get(url, headers=headers, params={"page": 1, "pageSize": page_size})
        response.raise_for_status()
        data =response.json()

        total_items = data["totalItems"]
        total_pages = math.ceil(total_items / page_size)

        all_instruments = data["items"]

        #Run through remaining pages to collect all instrumes
        for page in range(2, total_pages + 1):
            response = requests.get(url, headers=headers, params={"page": page, "pageSize": page_size})
            response.raise_for_status()
            
            data = response.json()
            all_instruments.extend(data["items"])
        
        return all_instruments
    except Exception as e:
        print(f"Error loading instruments: {e}")
        return None

#Loop and push to stream daily
while True:
    instruments = fetch_instruments()
    if instruments:
        print(">>Producing instrument mapping")
        for instrument in instruments:
            producer.send("instruments", value = instrument)
        print(f">>Instrument mapping sent to consumer for {len(instruments)} instruments")
    else:
        print(">>Attempting retry...")
        time.sleep(60)
        instruments = fetch_instruments()
        if instruments:
            print(">>Producing instrument mapping")
            for instrument in instruments:
                producer.send("instruments", value = instrument)
            print(f">>Instrument mapping sent to consumer for {len(instruments)} instruments")
    time.sleep(86400)
