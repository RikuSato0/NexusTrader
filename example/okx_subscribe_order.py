import asyncio
import uvloop


from pprint import pprint


from tradebot.exchange import OkxWebsocketManager
from tradebot.constants import CONFIG, Url

OKX_API_KEY = CONFIG['okex_demo']['API_KEY']
OKX_SECRET = CONFIG['okex_demo']['SECRET']
OKX_PASSPHRASE = CONFIG['okex_demo']['PASSPHRASE']
OKX_USER = CONFIG['okex_demo']['USER']


def cb(msg):
    """
    Order message callback:
        {'event': 'login', 'msg': '', 'code': '0', 'connId': '06c5a49b'}
        {'event': 'subscribe', 'arg': {'channel': 'orders', 'instType': 'ANY'}, 'connId': '06c5a49b'}
        {'event': 'channel-conn-count', 'channel': 'orders', 'connCount': '1', 'connId': '06c5a49b'}
    {'arg': {'channel': 'orders', 'instType': 'ANY', 'uid': '422205842008504732'},
     'data': [{'accFillSz': '0',
               'algoClOrdId': '',
               'algoId': '',
               'amendResult': '',
               'amendSource': '',
               'attachAlgoClOrdId': '',
               'attachAlgoOrds': [],
               'avgPx': '0',
               'cTime': '1726066189031',
               'cancelSource': '',
               'category': 'normal',
               'ccy': '',
               'clOrdId': '',
               'code': '0',
               'execType': '',
               'fee': '0',
               'feeCcy': 'USDT',
               'fillFee': '0',
               'fillFeeCcy': '',
               'fillFwdPx': '',
               'fillMarkPx': '',
               'fillMarkVol': '',
               'fillNotionalUsd': '',
               'fillPnl': '0',
               'fillPx': '',
               'fillPxUsd': '',
               'fillPxVol': '',
               'fillSz': '0',
               'fillTime': '',
               'instId': 'BTC-USDT-SWAP',
               'instType': 'SWAP',
               'isTpLimit': 'false',
               'lastPx': '55621',
               'lever': '0',
               'linkedAlgoOrd': {'algoId': ''},
               'msg': '',
               'notionalUsd': '55641.57977',
               'ordId': '1797302516729970688',
               'ordType': 'market',
               'pnl': '0',
               'posSide': 'net',
               'px': '',
               'pxType': '',
               'pxUsd': '',
               'pxVol': '',
               'quickMgnType': '',
               'rebate': '0',
               'rebateCcy': 'USDT',
               'reduceOnly': 'false',
               'reqId': '',
               'side': 'buy',
               'slOrdPx': '0',
               'slTriggerPx': '0',
               'slTriggerPxType': '',
               'source': '',
               'state': 'live',
               'stpId': '',
               'stpMode': 'cancel_maker',
               'sz': '1000',
               'tag': '',
               'tdMode': 'cross',
               'tgtCcy': '',
               'tpOrdPx': '0',
               'tpTriggerPx': '0',
               'tpTriggerPxType': '',
               'tradeId': '',
               'uTime': '1726066189031'}]}
    {'arg': {'channel': 'orders', 'instType': 'ANY', 'uid': '422205842008504732'},
     'data': [{'accFillSz': '1000',
               'algoClOrdId': '',
               'algoId': '',
               'amendResult': '',
               'amendSource': '',
               'attachAlgoClOrdId': '',
               'attachAlgoOrds': [],
               'avgPx': '55621.8',
               'cTime': '1726066189031',
               'cancelSource': '',
               'category': 'normal',
               'ccy': '',
               'clOrdId': '',
               'code': '0',
               'execType': 'T',
               'fee': '-27.8109',
               'feeCcy': 'USDT',
               'fillFee': '-27.8109',
               'fillFeeCcy': 'USDT',
               'fillFwdPx': '',
               'fillMarkPx': '55623.1',
               'fillMarkVol': '',
               'fillNotionalUsd': '55642.380066000005',
               'fillPnl': '78.4',
               'fillPx': '55621.8',
               'fillPxUsd': '',
               'fillPxVol': '',
               'fillSz': '1000',
               'fillTime': '1726066189033',
               'instId': 'BTC-USDT-SWAP',
               'instType': 'SWAP',
               'isTpLimit': 'false',
               'lastPx': '55621.8',
               'lever': '0',
               'linkedAlgoOrd': {'algoId': ''},
               'msg': '',
               'notionalUsd': '55642.380066000005',
               'ordId': '1797302516729970688',
               'ordType': 'market',
               'pnl': '78.4',
               'posSide': 'net',
               'px': '',
               'pxType': '',
               'pxUsd': '',
               'pxVol': '',
               'quickMgnType': '',
               'rebate': '0',
               'rebateCcy': 'USDT',
               'reduceOnly': 'false',
               'reqId': '',
               'side': 'buy',
               'slOrdPx': '',
               'slTriggerPx': '',
               'slTriggerPxType': '',
               'source': '',
               'state': 'filled',
               'stpId': '',
               'stpMode': 'cancel_maker',
               'sz': '1000',
               'tag': '',
               'tdMode': 'cross',
               'tgtCcy': '',
               'tpOrdPx': '',
               'tpTriggerPx': '',
               'tpTriggerPxType': '',
               'tradeId': '1189265987',
               'uTime': '1726066189033'}]}
    """
    pprint(msg)
    
async def main():
    try:        
        okx_ws_manager = OkxWebsocketManager(url=Url.Okx.Demo, api_key=OKX_API_KEY, secret=OKX_SECRET, passphrase=OKX_PASSPHRASE)
        await okx_ws_manager.subscribe_order(callback=cb)
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await okx_ws_manager.close()
        print("Websocket closed.")

if __name__ == "__main__":
    uvloop.run(main())
