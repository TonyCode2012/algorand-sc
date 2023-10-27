from beaker import Application, GlobalStateValue, Authorize
from beaker.lib.storage import BoxMapping, BoxList
import pyteal as pt

class StorageOrderState:
    base_price = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        desr="Storage order base price per file"
    )
    byte_price = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        desr="Storage order byte price"
    )
    size_limit = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        desr="File size limit"
    )
    service_rate = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        desr="Service rate for the real place order node"
    )
    node_num = GlobalStateValue(
        stack_type=pt.TealType.uint64,
        desr="Order node number"
    )
    node_array=BoxList(pt.abi.Address, 30)
    nodes=BoxMapping(pt.abi.Address, pt.TealType.uint64)

def storage_order_blueprint(app: Application) -> None:
    @app.external(authorize=Authorize.only_creator())
    def set_base_price(price: pt.abi.Uint64) -> pt.Expr:
        return app.state.base_price.set(price)

    @app.external(authorize=Authorize.only_creator())
    def set_byte_price(price: pt.abi.Uint64) -> pt.Expr:
        return app.state.byte_price.set(price)

    @app.external(authorize=Authorize.only_creator())
    def set_size_limit(size: pt.abi.Uint64) -> pt.Expr:
        return app.state.size_limit.set(size)

    @app.external(authorize=Authorize.only_creator())
    def set_service_rate(rate: pt.abi.Uint64) -> pt.Expr:
        return app.state.service_rate.set(rate)

    @app.external(authorize=Authorize.only_creator())
    def set_all_state(base_price: pt.abi.Uint64, byte_price: pt.abi.Uint64, size_limit: pt.abi.Uint64, service_rate: pt.abi.Uint64) -> pt.Expr:
        return pt.Seq(
            app.state.base_price.set(base_price),
            app.state.byte_price.set(byte_price),
            app.state.size_limit.set(size_limit),
            app.state.service_rate.set(service_rate),
        )

    @app.external(authorize=Authorize.only_creator())
    def add_order_node(address: pt.abi.Address) -> pt.Expr:
        return pt.Seq(
            pt.Assert(
                app.state.node_num < pt.Int(30),
                comment=f"Order node number has exceeded limit:{pt.Int(30)}",
            )
            pt.Assert(
                !app.state.nodes[address].exists(),
                comment=f"{address} has been added",
            ),
            app.state.nodes[address].set(app.state.node_num),
            app.state.node_array[node_num].set(address),
            app.state.node_num.set(app.state.node_num + pt.Int(1)),
        )

    @app.external(authorize=Authorize.only_creator())
    def remove_order_node(address: pt.abi.Address) -> pt.Expr:
        return pt.Seq(
            pt.Assert(
                app.state.node_num > pt.Int(0),
                comment="No node to remove",
            ),
            pt.Assert(
                app.state.nodes[address].exists(),
                comment=f"{address} not exist",
            ),
            If(app.state.node_num.box_size == pt.Int(1))
            .Then(app.state.node_num.set(pt.Int(0)))
            .Else(
                pt.Seq(
                    last_address=ScratchVar(pt.abi.Address),
                    deleted_position=ScratchVar(pt.TealType.uint64),
                    last_address.store(app.state.nodes[app.state.node_num - pt.Int(1)]),
                    deleted_position.store(app.state.nodes[address].get()),
                    # Replace deleted position with the last element
                    app.state.node_array[deleted_position.load()].set(last_address.load()),
                    # Update the last element's position to the deleted one's
                    app.state.nodes[last_address.load()].set(deleted_position.load()),
                    app.state.node_num.set(app.state.node_num - pt.Int(1)),
                )
            ),
            app.state.nodes[address].delete(),
        )

    @app.external
    def get_price(size: pt.abi.Uint64, is_permanent: pt.abi.Bool, *, output: pt.abi.Uint64) -> pt.Expr:
        price = ScratchVar(pt.TealType.uint64)
        price.store((app.state.base_price + size.get() * app.state.byte_price / pt.Int(1024) / pt.Int(1024)) * (app.state.service_rate + pt.Int(100)) / pt.Int(100))
        return pt.Seq(
            If(is_permanent.get())
            .Then(output.set(price.load() * 200))
            .Else(output.set(price.load()))
        )

    @app.external
    def place_order(cid: pt.abi.String, size: pt.abi.Uint64, is_permanent: pt.abi.Bool) -> pt.Expr:
        node = ScratchVar(pt.abi.Address)
        price = ScratchVar(pt.abi.Uint64)
        return pt.Seq(
            pt.Assert(
                app.state.node_num > 0,
                comment="No node to order",
            ),
            pt.Assert(
                size.get() <= app.state.size_limit,
                comment=f"Given file size:{size.get()} exceeds size limit:{app.state.size_limit}"
            ),
            price.store(self.get_price(size, is_permanent)),
            pt.Assert(
                price < pt.Balance(pt.Txn.sender()),
                comment="Insufficient balance to place order",
            ),
            node.store(pt.state.node_array[pt.Global.round() % app.state.node_num]),
            pt.InnerTxnBuilder.Execute(
                {
                    pt.TxnField.type_enum: pt.TxnType.Payment,
                    pt.TxnField.amount: price,
                    pt.TxnField.receiver: node.load(),
                    pt.TxnField.sender: pt.Txn.sender(),
                    pt.TxnField.fee: pt.Int(0),
                }
            ),
            pt.Log(f"\{'customer':{pt.Txn.sender()},'merchant':{node.load()},'cid':{cid.get()},'size':{size.get()},'price':{price.load()},'is_permanent':{isPermanent.get()}\}"),
        )

app = Application("StorageOrder", desr="This is storage order contract used to place order", state=StorageOrderState)
app.apply(storage_order_blueprint)
