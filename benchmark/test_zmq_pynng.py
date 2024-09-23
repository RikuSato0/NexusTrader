import time
import zmq
import pynng
import asyncio
import uvloop

N = 100000


def zmq_p2p_test(num_messages=N):
    context = zmq.Context()
    socket_send = context.socket(zmq.PUSH)
    socket_recv = context.socket(zmq.PULL)
    socket_send.bind("tcp://127.0.0.1:5555")
    socket_recv.connect("tcp://127.0.0.1:5555")

    start_time = time.time()
    for i in range(num_messages):
        socket_send.send_string(f"Message {i}")
        message = socket_recv.recv_string()
    end_time = time.time()

    socket_send.close()
    socket_recv.close()
    context.term()
    return end_time - start_time


def zmq_pubsub_test(num_messages=N):
    context = zmq.Context()
    socket_pub = context.socket(zmq.PUB)
    socket_sub = context.socket(zmq.SUB)

    socket_pub.bind("tcp://127.0.0.1:5556")
    socket_sub.connect("tcp://127.0.0.1:5556")

    # 设置订阅
    socket_sub.setsockopt(zmq.SUBSCRIBE, b"")

    # 给连接一些时间来建立
    time.sleep(0.01)

    # 发送一个同步消息
    socket_pub.send_string("START")
    socket_sub.recv_string()

    start_time = time.time()
    for i in range(num_messages):
        socket_pub.send_string(f"Message {i}")
        message = socket_sub.recv_string()
        # print(message)
    end_time = time.time()

    # 发送结束消息
    socket_pub.send_string("END")
    socket_sub.recv_string()

    socket_pub.close()
    socket_sub.close()
    context.term()
    return end_time - start_time


async def nng_p2p_test(num_messages=N):
    async def sender(addr):
        with pynng.Pair0() as s:
            s.listen(addr)
            await s.asend(b"start")
            for i in range(num_messages):
                await s.asend(f"Message {i}".encode())
            await s.asend(b"end")

    async def receiver(addr):
        with pynng.Pair0() as s:
            s.dial(addr)
            start_msg = await s.arecv()
            if start_msg != b"start":
                raise RuntimeError("Did not receive start message")

            for i in range(num_messages):
                msg = await s.arecv()

            end_msg = await s.arecv()
            if end_msg != b"end":
                raise RuntimeError("Did not receive end message")

    addr = "tcp://127.0.0.1:5557"
    start_time = time.time()

    sender_task = asyncio.create_task(sender(addr))
    receiver_task = asyncio.create_task(receiver(addr))

    try:
        await asyncio.wait_for(
            asyncio.gather(sender_task, receiver_task), timeout=30
        )  # 30 seconds timeout
    except asyncio.TimeoutError:
        print("NNG P2P test timed out after 30 seconds")
        return None
    # except Exception as e:
    #     print(f"An error occurred during NNG P2P test: {e}")
    #     return None

    end_time = time.time()
    return end_time - start_time


async def nng_pubsub_test(num_messages=N):
    with pynng.Pub0() as pub, pynng.Sub0() as sub:
        pub.listen("tcp://127.0.0.1:5558")
        sub.dial("tcp://127.0.0.1:5558")
        sub.subscribe(b"")
        await asyncio.sleep(0.01)  # Allow time for subscription to be established

        start_time = time.time()
        for i in range(num_messages):
            await pub.asend(f"Message {i}".encode())
            message = await sub.arecv()
        end_time = time.time()

    return end_time - start_time


def main_zmq():
    print("ZMQ Point-to-Point test:")
    zmq_p2p_time = zmq_p2p_test()
    print(f"Time taken: {zmq_p2p_time:.4f} seconds")

    print("\nZMQ Pub-Sub test:")
    zmq_pubsub_time = zmq_pubsub_test()
    print(f"Time taken: {zmq_pubsub_time:.4f} seconds")


async def main_pynng():
    print("\nNNG Point-to-Point test:")
    nng_p2p_time = await nng_p2p_test()
    print(f"Time taken: {nng_p2p_time:.4f} seconds")

    print("\nNNG Pub-Sub test:")
    nng_pubsub_time = await nng_pubsub_test()
    print(f"Time taken: {nng_pubsub_time:.4f} seconds")


if __name__ == "__main__":
    main_zmq()
    uvloop.run(main_pynng())
