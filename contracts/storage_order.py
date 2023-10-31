from beaker import Application, GlobalStateValue, Authorize, BuildOptions
from beaker.lib.storage import BoxMapping, BoxList
import pyteal as pt
from beaker.consts import (
    ASSET_MIN_BALANCE,
    BOX_BYTE_MIN_BALANCE,
    BOX_FLAT_MIN_BALANCE,
    FALSE,
)
from algosdk.encoding import decode_address, encode_address
import algosdk
import base64

class StorageOrderState:
    base_price = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="Storage order base price per file"
    )
    byte_price = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="Storage order byte price"
    )
    size_limit = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="File size limit"
    )
    service_rate = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="Service rate for the real place order node"
    )
    algo_cru_rate = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        descr="ALGO to CRU exchange rate"
    )
    node_num = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        default=pt.Int(0),
        descr="Order node number"
    )
    nodes=BoxList(pt.abi.Address, 10)
    node_map=BoxMapping(pt.abi.Address, pt.abi.Uint64)
    minimum_balance=pt.Int(0)

    def __init__(self):
        self.minimum_balance = pt.Int(
            (
                BOX_FLAT_MIN_BALANCE
                + (pt.abi.size_of(pt.abi.Uint64) * BOX_BYTE_MIN_BALANCE)
                + (pt.abi.size_of(pt.abi.Address) * BOX_BYTE_MIN_BALANCE)
            )
            + (
                BOX_FLAT_MIN_BALANCE
                + (self.nodes.box_size.value * BOX_BYTE_MIN_BALANCE)
            )
        )

app = Application(
    "StorageOrder",
    descr="This is storage order contract used to place order",
    state=StorageOrderState(),
    #build_options=BuildOptions(scratch_slots=False),
)

def storage_order_blueprint(app: Application) -> None:
    @app.external(authorize=Authorize.only_creator())
    def bootstrap(
        seed: pt.abi.PaymentTransaction,
        base_price: pt.abi.Uint64,
        byte_price: pt.abi.Uint64,
        size_limit: pt.abi.Uint64,
        service_rate: pt.abi.Uint64,
        algo_cru_rate: pt.abi.Uint64
    ) -> pt.Expr:
        return pt.Seq(
	    pt.Assert(
                seed.get().receiver() == pt.Global.current_application_address(),
                comment="payment must be to app address",
            ),
            pt.Assert(
                seed.get().amount() >= app.state.minimum_balance,
                comment=f"payment must be for >= {app.state.minimum_balance.value}",
            ),
            pt.Pop(app.state.nodes.create()),
            app.state.base_price.set(base_price.get()),
            app.state.byte_price.set(byte_price.get()),
            app.state.size_limit.set(size_limit.get()),
            app.state.service_rate.set(service_rate.get()),
            app.state.algo_cru_rate.set(algo_cru_rate.get()),
        )

    @app.external(authorize=Authorize.only_creator())
    def set_base_price(price: pt.abi.Uint64) -> pt.Expr:
        return app.state.base_price.set(price.get())

    @app.external(authorize=Authorize.only_creator())
    def set_byte_price(price: pt.abi.Uint64) -> pt.Expr:
        return app.state.byte_price.set(price.get())

    @app.external(authorize=Authorize.only_creator())
    def set_size_limit(size: pt.abi.Uint64) -> pt.Expr:
        return app.state.size_limit.set(size.get())

    @app.external(authorize=Authorize.only_creator())
    def set_service_rate(rate: pt.abi.Uint64) -> pt.Expr:
        return app.state.service_rate.set(rate.get())

    @app.external(authorize=Authorize.only_creator())
    def set_algo_cru_rate(rate: pt.abi.Uint64) -> pt.Expr:
        return app.state.algo_cru_rate.set(rate.get())

    @app.external(authorize=Authorize.only_creator())
    def add_order_node(address: pt.abi.Address) -> pt.Expr:
        return pt.Seq(
            pt.Assert(
                app.state.node_num < app.state.nodes.elements,
                comment=f"order node number has exceeded limit:{app.state.nodes.elements}",
            ),
            pt.Assert(
                pt.Not(app.state.node_map[address].exists()),
                comment=f"{address} has been added",
            ),
            (node_num := pt.abi.Uint64()).set(app.state.node_num),
            app.state.node_map[address].set(node_num),
            app.state.nodes[app.state.node_num].set(address),
            app.state.node_num.set(app.state.node_num + pt.Int(1)),
        )

    @app.external(authorize=Authorize.only_creator())
    def remove_order_node(address: pt.abi.Address) -> pt.Expr:
        last_address=pt.abi.Address()
        deleted_position=pt.abi.Uint64()
        return pt.Seq(
            pt.Assert(
                app.state.node_num > pt.Int(0),
                comment="no node to remove",
            ),
            pt.Assert(
                app.state.node_map[address].exists(),
                comment=f"{address} not exist",
            ),
            pt.If(app.state.node_num == pt.Int(1))
            .Then(app.state.node_num.set(pt.Int(0)))
            .Else(
                pt.Seq(
                    app.state.nodes[app.state.node_num - pt.Int(1)].store_into(last_address),
                    app.state.node_map[address].store_into(deleted_position),
                    # Replace deleted position with the last element
                    app.state.nodes[deleted_position.get()].set(last_address),
                    # Update the last element's position to the deleted one's
                    app.state.node_map[last_address.get()].set(deleted_position),
                    app.state.node_num.set(app.state.node_num - pt.Int(1)),
                )
            ),
            pt.Pop(app.state.node_map[address].delete())
        )

    @app.external(read_only=True)
    def get_random_order_node(*, output: pt.abi.Address) -> pt.Expr:
        return pt.Seq(
            pt.Assert(
                app.state.node_num > pt.Int(0),
                comment="no node to order",
            ),
            output.set(app.state.nodes[pt.Global.round() % app.state.node_num].get()),
        )

    @app.external(read_only=True)
    def get_price(
        size: pt.abi.Uint64,
        is_permanent: pt.abi.Bool,
        *,
        output: pt.abi.Uint64
    ) -> pt.Expr:
        return output.set(_get_price(size, is_permanent))

    @app.external
    def place_order(
        seed: pt.abi.PaymentTransaction,
        merchant: pt.abi.Account,
        cid: pt.abi.String,
        size: pt.abi.Uint64,
        is_permanent: pt.abi.Bool
    ) -> pt.Expr:
        price = pt.ScratchVar(pt.TealType.uint64)
        return pt.Seq(
            pt.Assert(
                seed.get().receiver() == pt.Global.current_application_address(),
                comment="payment must be to app address",
            ),
            pt.Assert(
                app.state.node_num > pt.Int(0),
                comment="no node to order",
            ),
            pt.Assert(
                app.state.node_map[merchant.address()].exists(),
                comment=f"{merchant.address()} is not an order node",
            ),
            pt.Assert(
                size.get() <= app.state.size_limit,
                comment=f"given file size:{size.get()} exceeds size limit:{app.state.size_limit}"
            ),
            price.store(_get_price(size, is_permanent)),
            pt.Assert(
                seed.get().amount() >= price.load(),
                comment=f"payment must be for >= {app.state.minimum_balance.value}",
            ),
            # Pay to merchant
            pt.InnerTxnBuilder.Execute(
                {
                    pt.TxnField.type_enum: pt.TxnType.Payment,
                    pt.TxnField.amount: price.load(),
                    pt.TxnField.receiver: merchant.address(),
                }
            ),
            # Refund exceeded fee to customer
            pt.If(seed.get().amount() - price.load() > pt.Int(0))
            .Then(
                pt.InnerTxnBuilder.Execute(
                    {
                        pt.TxnField.type_enum: pt.TxnType.Payment,
                        pt.TxnField.amount: seed.get().amount() - price.load(),
                        pt.TxnField.sender: pt.Txn.sender(),
                    }
                )
            ),
            (address := pt.abi.String()).set(merchant.address()),
            pt.Log(
                pt.Concat(
                    pt.Bytes("$customer$"),pt.Txn.sender(),pt.Bytes("$customer_end$"),
                    pt.Bytes("$merchant$"),merchant.address(),pt.Bytes("$merchant_end$"),
                    pt.Bytes("$cid$"),cid.get(),pt.Bytes("$cid_end$"),
                    pt.Bytes("$size$"),pt.Itob(size.get()),pt.Bytes("$size_end$"),
                    pt.Bytes("$price$"),pt.Itob(price.load()),pt.Bytes("$price_end$"),
                    pt.Bytes("$is_permanent$"),pt.Itob(is_permanent.get()),pt.Bytes("$is_permanent_end$"),
                )
            ),
        )

    def _get_price(
        size: pt.abi.Uint64,
        is_permanent: pt.abi.Bool
    ) -> pt.TealType.uint64:
        price = pt.ScratchVar(pt.TealType.uint64)
        return pt.Seq(
            price.store(
                (app.state.base_price + size.get() * app.state.byte_price / pt.Int(1024) / pt.Int(1024)) * (app.state.service_rate + pt.Int(100)) / pt.Int(100) / app.state.algo_cru_rate
            ),
            pt.If(is_permanent.get())
            .Then(price.load() * pt.Int(200))
            .Else(price.load())
        )

app.apply(storage_order_blueprint)

app.build().export("./artifacts")
print("Build smart contract successfully")
