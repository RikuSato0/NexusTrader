import uvloop
from picows import ws_connect, WSFrame, WSTransport, WSListener, WSMsgType, WSCloseCode


class WsClient(WSListener):
    def on_ws_connected(self, transport: WSTransport):
        print("Connected...")

    def on_ws_frame(self, transport: WSTransport, frame: WSFrame):
        if frame.msg_type == WSMsgType.PING:
            return

    def on_close(self, code: WSCloseCode):
        print(f"Connection closed with code: {code}")
