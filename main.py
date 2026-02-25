
import os,RNS,time
from DNSServer import Server
from RDNSInteraction import AnnounceHandler,get_peers,RDNS_INIT,RDNS_VOTE
from ServerIdentity import getIdentity

APP_NAME = "RDNS_SERVER"
DNServer = Server()

ANNOUNCE_INTERVAL = 5*60


def add_destination(path,handler):
    dest = RNS.Destination(
        getIdentity(),
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        APP_NAME,
        path
    )
    dest.register_request_handler(path,handler,allow = RNS.Destination.ALLOW_ALL)
    dest.set_proof_strategy(RNS.Destination.PROVE_ALL)
    return dest

def request_handle(path, data, request_id, link_id, remote_identity, requested_at):
    destination_hash = None
    if remote_identity:
        destination_hash = RNS.Destination.hash(remote_identity,"RDNS_SERVER","RDNS_SERVER")
    RNS.log(f"Received request: {data} from {destination_hash}" )
    if data.startswith(b"RDNS_QUERY"):
        return query_handler(data=data[len("RDNS_QUERY"):])
    elif data.startswith(b"RDNS_GET_PEERS"):
        return b"".join(get_peers())
    elif data.startswith(b"RDNS_GET_HASH"):
        return DNServer.get_db_hash()
    elif data.startswith(b"RDNS_GET_TABLE"):
        return DNServer.get_db()
    elif data.startswith(b"RDNS_INIT") and destination_hash != None:
        return RDNS_INIT(destination_hash)
    elif data.startswith(b"RDNS_VOTE") and destination_hash != None:
        return RDNS_VOTE(destination_hash)

def query_handler(data):
    try:
        result = DNServer.query(data.decode())
        if result == None:
            return "Not found"
        return result
    except Exception as e:
        return f"Failure: {e} "

def program_setup():

    reticulum = RNS.Reticulum()

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
