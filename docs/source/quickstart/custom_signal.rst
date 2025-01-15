Custom Signal
==============

Define a signal sender
-----------------------------

You need to send your trading signal to a zmq server. Here we are using the ``ipc`` protocol to send the signal. The signal may have different formats, e.g., ``"BTCUSDT.BBP"``, so we need to format the signal into our trading bot's instrument ID format on the receiver side.

.. code-block:: python

    import zmq
    import orjson
    import time
    import sys

    # data is a list of mock trading signal
    datas = [
        [{
            "instrumentID": "BTCUSDT.BBP",
            "position": 200,
        }],
        # more trading signal
    ]
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind("ipc:///tmp/zmq_data_test")

    index = 0

    def main():
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

    if __name__ == "__main__":
        main()

