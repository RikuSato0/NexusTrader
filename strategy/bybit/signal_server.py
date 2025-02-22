import zmq
import orjson
import time
import sys



datas = [
    [{
        "instrumentID": "LDOUSDT.BBP",
        "position": 50,
    }],
    [{
        "instrumentID": "LDOUSDT.BBP",
        "position": 49,
    }],
    [{
        "instrumentID": "LDOUSDT.BBP",
        "position": 49,
    }],
    [{
        "instrumentID": "LDOUSDT.BBP",
        "position": 47,
    }],
    [{
        "instrumentID": "LDOUSDT.BBP",
        "position": 47,
    }],
    [{
        "instrumentID": "LDOUSDT.BBP",
        "position": 45,
    }],
    [{
        "instrumentID": "LDOUSDT.BBP",
        "position": 0,
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
        time.sleep(60)
        
except KeyboardInterrupt:
    print("Exiting...")
finally:
    socket.close()
    context.term()
    sys.exit(0)
