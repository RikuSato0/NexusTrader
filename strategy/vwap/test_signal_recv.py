import zmq.asyncio
import orjson
import sys
import asyncio

async def main():
    # Initialize ZMQ context and socket
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.SUB)
    socket.connect("ipc:///tmp/zmq_data_test")
    
    # Subscribe to all messages
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    
    print("Receiver started, waiting for messages...")
    
    try:
        while True:
            # Receive and decode message
            message = await socket.recv()
            data = orjson.loads(message)
            
            # Process the received data
            print(f"Received data: {data}")
            
            # Access specific fields if needed
            for item in data:
                instrument = item["instrumentID"]
                position = item["position"]
                print(f"Instrument: {instrument}, Position: {position}")
                
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        socket.close()
        context.term()
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
