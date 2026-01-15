# proto_inspect.py

import MarketDataFeedV3_pb2 as pb

print("Available attributes in MarketDataFeedV3_pb2:")
for attr in dir(pb):
    print(attr)
