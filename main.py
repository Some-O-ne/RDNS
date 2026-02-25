
import os,atexit,RNS,time
from DNSServer import Server
from RDNSInteraction import AnnounceHandler,get_peers,RDNS_INIT,RDNS_VOTE

APP_NAME = "RDNS_SERVER"
DNServer = Server()

IDENTITY_FILE_NAME = "identity"
identity = None

ANNOUNCE_INTERVAL = 5*60


def add_destination(path,handler):
    dest = RNS.Destination(
        identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        APP_NAME,
        path
    )
    dest.register_request_handler(path,handler,allow = RNS.Destination.ALLOW_ALL)
    dest.set_proof_strategy(RNS.Destination.PROVE_ALL)
    return dest

def request_handle(path, data, request_id, link_id, remote_identity, requested_at):
    RNS.log(f"Received request: {data} from {remote_identity} " )
    if data.startswith(b"RDNS_QUERY"):
        return query_handler(data=data[len("RDNS_QUERY"):])
    elif data.startswith(b"RDNS_GET_PEERS"):
        return b"".join(get_peers())
    elif data.startswith(b"RDNS_GET_HASH"):
        return DNServer.get_db_hash()
    elif data.startswith(b"RDNS_GET_TABLE"):
        return DNServer.get_db()
    elif data.startswith(b"RDNS_INIT"):
        return RDNS_INIT(remote_identity)
    elif data.startswith(b"RDNS_VOTE"):
        return RDNS_VOTE(remote_identity,data[len("RDNS_VOTE"):])

def query_handler(data):
    try:
        result = DNServer.query(data.decode())
        if result == None:
            return "Not found"
        return result
    except Exception as e:
        return f"Failure: {e} "

def program_setup():
    global identity

    if os.path.isfile(IDENTITY_FILE_NAME):
        try: identity = RNS.Identity.from_file(os.path.abspath(IDENTITY_FILE_NAME))
        except Exception as e: RNS.log(e)

    reticulum = RNS.Reticulum()

    if not identity:
        identity = RNS.Identity()

    # add_destination("RDNS_QUERY",      query_handler)
    # add_destination("RDNS_GET_PEERS", lambda path, data, request_id, link_id, remote_identity, requested_at: b"".join(get_peers()))
    # add_destination("RDNS_GET_HASH",  lambda path, data, request_id, link_id, remote_identity, requested_at: DNServer.get_db_hash())
    # add_destination("RDNS_GET_TABLE", lambda path, data, request_id, link_id, remote_identity, requested_at: DNServer.get_db())
    # add_destination("RDNS_INIT",      lambda path, data, request_id, link_id, remote_identity, requested_at: RDNS_INIT(remote_identity))
    # add_destination("RDNS_VOTE",      lambda path, data, request_id, link_id, remote_identity, requested_at: RDNS_VOTE(remote_identity,data))
    RNS.Transport.register_announce_handler(AnnounceHandler())

    dest = add_destination("RDNS_SERVER",request_handle)

    announceLoop(dest)

def announceLoop(dest):
    while True:
        dest.announce(app_data=b"RDNS_READY")
        RNS.log(
            "Sent RDNS_READY announce from "+
            RNS.prettyhexrep(dest.hash)+ " " + dest.name
        )
        time.sleep(ANNOUNCE_INTERVAL)


if __name__ == "__main__":
    program_setup()


@atexit.register
def at_exit():
    global identity
    if not os.path.isfile(IDENTITY_FILE_NAME):
        RNS.log("Saving identity to disk...")
        RNS.log(identity.to_file(os.path.abspath(IDENTITY_FILE_NAME)))
