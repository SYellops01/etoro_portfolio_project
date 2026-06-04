'''
This script will collect the existing client portfolio hourly and complete a 1000 day backfill for any new items sat within the portfolio
'''
#Import packages
import requests
import json
import time
import uuid
from kafka.errors import NoBrokersAvailable
from kafka import KafkaProducer
from src.producer.credentials import get_user_key, get_api_key

print("--------------------------------------------------")
print(">> Extracting trading portfolio from eToro...")
print("--------------------------------------------------")


#Define producer
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
def fetch_portfolio():
    '''
    Purpose:
    - Calls API containing current portfolio information. Returns this new portfolio and any new instruments for backfill if these exist.
    '''
    url = "https://public-api.etoro.com/api/v1/trading/info/portfolio"
    #Get relevant variables for API
    headers = {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key": get_api_key(),
        "x-user-key": get_user_key(),
    }
    #check for existing instrumements
    try:
        with open("./existing_instruments.json", "r") as f:
            existing_instruments = json.load(f)
    except:
        existing_instruments = []
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        #get current portfolio for output
        portfolio = data["clientPortfolio"]
        portfolio["fetched_at"] = int(time.time())

        #get current portfolio instruments
        instruments = []
        positions = portfolio["positions"]
        for position in positions:
            instruments.append(position.get("instrumentID"))
        mirror_trades = portfolio["mirrors"]
        for mirror in mirror_trades:
            positions = mirror["positions"]
            for position in positions:
                instruments.append(position.get("instrumentID"))
        instruments = set(instruments)

        #Get list of new instruments and write updated list back
        new_instruments = [x for x in instruments if x not in existing_instruments]
        existing_instruments.extend(new_instruments)
        with open("./existing_instruments.json", "w") as f:
            json.dump(existing_instruments, f)
        
        return portfolio, new_instruments, existing_instruments
    except Exception as e:
        print(f'Error loading portfolio: {e}')
        return None, None, None


def backfill_history(instrumentID):
    url = f"https://public-api.etoro.com/api/v1/market-data/instruments/{instrumentID}/history/candles/asc/OneDay/1000"
    #Get relevant variables for API
    headers = {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key": get_api_key(),
        "x-user-key": get_user_key(),
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["candles"]
    except Exception as e:
        print(f"Failed to retrieve backfill for {instrumentID}: {e}")
        return None

def get_current_market_price(instrumentID):
    url = f"https://public-api.etoro.com/api/v1/market-data/instruments/rates?instrumentIds={instrumentID}"
    #Get relevant variables for API
    headers = {
        "x-request-id": str(uuid.uuid4()),
        "x-api-key": get_api_key(),
        "x-user-key": get_user_key(),
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["rates"][0]
    except Exception as e:
        print(f"Failed to get market rate for {instrumentID}: {e}")
        return None

#initial sleep time to ensure rate limits not met
time.sleep(120)
#Loop and push to stream daily
while True:
    portfolio, new_instruments, existing_instruments = fetch_portfolio()
    if portfolio:
        print(">>Collecting latest portfolio")
        producer.send("portfolio", value = portfolio)
        print(">>Latest portfolio collected")
    time.sleep(60)
    #If new instruments exist, run backfill and send to stock-history topic
    if new_instruments:
        for instrument_id in new_instruments:
            history = backfill_history(instrument_id)
            if history:
                producer.send("stock-history", value = history)
        print(f">>Successfully backfilled for {len(new_instruments)} new instruments")
    time.sleep(60)
    if existing_instruments:
        for instrument_id in existing_instruments:
            market_price = get_current_market_price(instrument_id)
            if market_price:
                producer.send("stock-prices", value = market_price)
        print(f">>Latest stock prices collected for {len(existing_instruments)} instruments")
    time.sleep(180)
