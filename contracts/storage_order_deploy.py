from storage_order import app
from beaker import localnet, client
from algosdk.encoding import decode_address, encode_address
from algosdk.transaction import PaymentTxn
from algosdk.atomic_transaction_composer import TransactionWithSigner
import random
import base64
import json

#def find_in_bytes(start: bytes, end: bytes) -> bytes:

#log=base64.b64decode("eyJjdXN0b21lciI6Ij1bAGpavKlkQnKCNumhVtTKbY3Ox86Dv+xoSHV7R1w1IiwibWVyY2hhbnQiOiKPdTEut4gHPO7/NMo/f7F6FCJ8MeZrLQwej7F2d3SgkCIsImNpZCI6ImJhZmtyZWloamhqdnRieHp4bm1sY3dra21lYXliNzJ4ZXh4ZGxveWJqZGo2M2c1cGFzZnljN3prdnk0Iiwic2l6ZSI6IgAAAAAAAB5sIiwicHJpY2UiOiIAAAAAB7+oRCIsImlzX3Blcm1hbmVudCI6IgAAAAAAAAAAIix9")
#log=base64.b64decode("eyJjdXN0b21lciI6Ij1bAGpavKlkQnKCNumhVtTKbY3Ox86Dv+xoSHV7R1w1IiwibWVyY2hhbnQiOiKPdTEut4gHPO7/NMo/f7F6FCJ8MeZrLQwej7F2d3SgkCIsImNpZCI6ImJhZmtyZWloamhqdnRieHp4bm1sY3dra21lYXliNzJ4ZXh4ZGxveWJqZGo2M2c1cGFzZnljN3prdnk0Iiwic2l6ZSI6IgAAAAAAAB5sIiwicHJpY2UiOiIAAAAAB7+oRCIsImlzX3Blcm1hbmVudCI6IgAAAAAAAAAAIn0=")
#print(log)
#print(json.loads(str(log,"utf-8")))
#print(log.decode("utf-8"))
#print(encode_address("=[\x00jZ\xbc\xa9dBr\x826\xe9\xa1V\xd4\xcam\x8d\xce\xc7\xce\x83\xbf\xechHu{G\\5}]"))
#print(encode_address("=[jZ¼©dBr6é¡VÔÊmÎÇÎ¿ìhHu{G\5}]"))
#print(encode_address("jZbca9dBr826e9a1Vd4cam8dcec7ce83bfechHu{G\\5}]"))

log=base64.b64decode("Y3VzdG9tZXI6PVsAalq8qWRCcoI26aFW1Mptjc7HzoO/7GhIdXtHXDVjdXN0b21lcl9lbmRtZXJjaGFudDqPdTEut4gHPO7/NMo/f7F6FCJ8MeZrLQwej7F2d3SgkG1lcmNoYW50X2VuZGNpZDpiYWZrcmVpaGpoanZ0Ynh6eG5tbGN3a2ttZWF5YjcyeGV4eGRsb3liamRqNjNnNXBhc2Z5Yzd6a3Z5NGNpZEVuZHNpemU6AAAAAAAAHmxzaXplX2VuZHByaWNlOgAAAAAHv6hEcHJpY2VfZW5kaXNfcGVybWFuZW50OgAAAAAAAAAAaXNfcGVybWFuZW50X2VuZA==")
start=b"customer:"
end=b"customer_end"
sp=log.find(start)
ep=log.find(end)
print(f"customer:{encode_address(log[sp+len(start):ep])}")
start=b"merchant:"
end=b"merchant_end"
sp=log.find(start)
ep=log.find(end)
print(f"merchant:{encode_address(log[sp+len(start):ep])}")
start=b"cid:"
end=b"cidEnd"
sp=log.find(start)
ep=log.find(end)
print(f"cid:{log[sp+len(start):ep]}")
start=b"size:"
end=b"size_end"
sp=log.find(start)
ep=log.find(end)
print(f"size:{int.from_bytes(log[sp+len(start):ep], 'big')}")
start=b"price:"
end=b"price_end"
sp=log.find(start)
ep=log.find(end)
print(f"price:{int.from_bytes(log[sp+len(start):ep], 'big')}")

log=base64.b64decode("j3UxLreIBzzu/zTKP3+xehQifDHmay0MHo+xdnd0oJA=")
print(encode_address(b'\x8fu1.\xb7\x88\x07<\xee\xff4\xca?\x7f\xb1z\x14"|1\xe6k-\x0c\x1e\x8f\xb1vwt\xa0\x90'))
print(encode_address(b'=[\x00jZ\xbc\xa9dBr\x826\xe9\xa1V\xd4\xcam\x8d\xce\xc7\xce\x83\xbf\xechHu{G\\5'))
print(encode_address(log))
exit()

accounts = localnet.kmd.get_accounts()
sender = accounts[0]
order_node = accounts[1]

app_client = client.ApplicationClient(
    client=localnet.get_algod_client(),
    app=app,
    sender=sender.address,
    signer=sender.signer,
)

app_id, app_addr, txid = app_client.create()
print(
    f"""
Deployed app in txid {txid}
App ID: {app_id}
App Address: {app_addr}
"""
)

print(localnet.get_algod_client())

sp = app_client.get_suggested_params()
sp.flat_fee = True
sp.fee = 4000
ptxn = PaymentTxn(
    sender.address,
    sp,
    app_client.app_addr,
    app.state.minimum_balance.value * 2,
)

app_client.call(
    "bootstrap",
    seed=TransactionWithSigner(ptxn, sender.signer),
    base_price=100000000,
    byte_price=100000,
    size_limit=209715200,
    service_rate=30,
    boxes=[(app_client.app_id, "nodes")] * 8,
)

print("===== Add order node =====")
print(f"order node address:{order_node.address}")
app_client.call(
    "add_order_node",
    address=order_node.address,
    boxes=[(app_client.app_id, decode_address(order_node.address)),(app_client.app_id, "nodes")],
)

#print("===== Remove order node =====")
#app_client.call(
#    "remove_order_node",
#    address=order_node.address,
#    boxes=[(app_client.app_id, decode_address(order_node.address)),(app_client.app_id, "nodes")],
#)

cid="bafkreihjhjvtbxzxnmlcwkkmeayb72xexxdloybjdj63g5pasfyc7zkvy4"
file_size=7788
print("===== Get price =====")
price = app_client.call("get_price", size=file_size, is_permanent=False).return_value
print(f"get_price => {price}")

print("===== Get order node randomly =====")
order_node_address=app_client.call(
    "get_random_order_node",
    boxes=[(app_client.app_id, "nodes")],
).return_value

print("===== Place order =====")
sp = app_client.get_suggested_params()
sp.flat_fee = True
sp.fee = 2000
ptxn = PaymentTxn(
    sender.address,
    sp,
    app_client.app_addr,
    price,
)
app_client.call(
    "place_order",
    seed=TransactionWithSigner(ptxn, sender.signer),
    merchant=order_node_address,
    cid=cid,
    size=file_size,
    is_permanent=False,
    boxes=[(app_client.app_id, decode_address(order_node_address)),(app_client.app_id, "nodes")],
)
