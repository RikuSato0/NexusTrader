import zmq
import orjson
import time
import sys



datas = [
    [{
        "instrumentID": "BTCUSDT.BBP",
        "position": 200,
    }],
    [{
        "instrumentID": "BTCUSDT.BBP",
        "position": 400,
    }],
    [{
        "instrumentID": "BTCUSDT.BBP",
        "position": 0,
    }],
    [{
        "instrumentID": "BTCUSDT.BBP",
        "position": 100,
    }],
    [{
        "instrumentID": "BTCUSDT.BBP",
        "position": -200,
    }],
    [{
        "instrumentID": "BTCUSDT.BBP",
        "position": -400,
    }],
    [{
        "instrumentID": "BTCUSDT.BBP",
        "position": -100,
    }],
]
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("ipc:///tmp/zmq_data_test")

index = 0

try:
    time.sleep(5)
    print("Server started, sending data...")
    
    while True:
        print(f"Sending data {datas[index]}")
        data = datas[index]
        socket.send(orjson.dumps(data))
        index += 1
        if index == len(datas):
            index = 0
        time.sleep(5)
        
except KeyboardInterrupt:
    print("Exiting...")
finally:
    socket.close()
    context.term()
    sys.exit(0)
