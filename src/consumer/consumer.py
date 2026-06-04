#Import requirments
import json
import boto3
import time
from kafka.errors import NoBrokersAvailable
from kafka import KafkaConsumer

#Establish minIO Connection
s3 = boto3.client(
    "s3",
    endpoint_url = "http://minio:9000",
    aws_access_key_id = "admin",
    aws_secret_access_key = "password123"
)

#Define buckets and create if not exists
topic_bucket_mapping = {
    "instruments" : "bronze-instruments",
    "portfolio" : "bronze-portfolio",
    "stock-history" : "bronze-stock-history",
    "stock-prices" : "bronze-stock-prices"
}

for bucket_name in topic_bucket_mapping.values():
    try:
        s3.head_bucket(Bucket = bucket_name)
    except:
        s3.create_bucket(Bucket = bucket_name)
        print(f"Created new bucket - {bucket_name}")

#Create Kafka consumer
def create_consumer():
    while True:
        try:
            consumer = KafkaConsumer(
                *topic_bucket_mapping.keys(),
                bootstrap_servers = ["kafka:9092"],
                auto_offset_reset = "earliest",
                enable_auto_commit = True,
                group_id = "bronze-consumer",
                value_deserializer = lambda x: json.loads(x.decode("utf-8"))
            )
            return consumer
        except NoBrokersAvailable:
            print("Waiting for kafka...")
            time.sleep(3)

consumer = create_consumer()

print("Consuming to minIO...")

for message in consumer:
    #Get topic, record and and bucket name
    topic = message.topic
    print(f"Topic: {topic} received...")
    record = message.value
    bucket_name = topic_bucket_mapping[topic]

    #conditional logic to get instrument id depending on bucket name
    if topic == "stock-prices":
        instrument_id = record.get("instrumentID", "unknown")
    elif topic == "stock-history":
        instrument_id = record[0].get("instrumentId", "unnknown")
    else:
        instrument_id = "all_instruments"
    timestamp = int(time.time())
    key = f"{instrument_id}/{timestamp}"

    #Put to bucket
    s3.put_object(
        Bucket = bucket_name,
        Key = key,
        Body = json.dumps(record),
        ContentType="application/json"
    )
    print(f">>Saved record for {instrument_id} to s3://{bucket_name}/{key}")