from storage_order import app
from beaker import sandbox, client

app.build.export("./artifacts")

accounts = sandbox.kmd.get_accounts()
sender = accounts[0]

app_client = client.ApplicationClient(
    client=sandbox.get_algod_client(),
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
