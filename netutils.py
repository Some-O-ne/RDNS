import RNS,hashlib
from collections import Counter
def establish_link(server_destination:RNS.Destination):
    link = RNS.Link(server_destination)

    server_link = None

    should_quit = False

    def established_link(link):
        nonlocal server_link
        server_link = link
    def link_closed(_):
        nonlocal should_quit
        should_quit = True

    link.set_link_established_callback(established_link)
    link.set_link_closed_callback(link_closed)

    if not should_quit and not server_link:
        time.sleep(0.1)
    return server_link,link

def request(server_link:RNS.Link,path:str,data=None):
    response = None
    should_quit = False

    def got_response(resp):
        nonlocal response
        response = resp.response
    
    def request_failed(_):
        nonlocal should_quit
        should_quit = True

    server_link.request(
        path,
        data = data,
        response_callback = got_response,
        failed_callback = request_failed
    )

    if not should_quit and not response:
        time.sleep(0.1)
    return response

def sendRequest(destination_hash,path,data=None):
    if not RNS.Transport.has_path(destination_hash):
        RNS.log("Destination is not yet known. Requesting path and waiting for announce to arrive...")
        RNS.Transport.request_path(destination_hash)
        while not RNS.Transport.has_path(destination_hash):
            time.sleep(0.1)

    server_identity = RNS.Identity.recall(destination_hash)

    RNS.log(f"Establishing link with {RNS.prettyhexrep(destination_hash)}...")

    server_destination = RNS.Destination(
        server_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        APP_NAME,
        "RDNS"
    )
    server_link,link = establish_link(server_destination)

    while not server_link:
        RNS.log("Couldn't connect to the server, retrying...")
        server_link,link = establish_link(server_destination)

    response = request(server_link,path,data)
    link.teardown()
    
    return response

def syncDB(peers,consensus):
    peer_table_hashes = {}
    for peer in peers:
            if peer == b"": continue

            table_hash = sendRequest(peer,"RDNS_GET_HASH")
            if type(table_hash)!=bytes or len(table_hash) != 32:
                continue
            
            peer_table_hashes[peer] = table_hash

    most_common_hash = Counter(peer_table_hashes.values()).most_common(1)[0]

    hash_amount = most_common_hash[1]
    most_common_hash = most_common_hash[0]

    if hash_amount/len(peers) < consensus:
        RNS.log("This network doesn't have any consensus, soooo, no thank you :3")
        peers = []

        return

    RNS.log("Trying to get the DNS table from RDNS....")
    for peer in peer_table_hashes:
        peer_hash = peer_table_hashes[peer]
        if peer_hash != most_common_hash:
            continue

        table = sendRequest(peer,"RDNS_GET_TABLE")
        if hashlib.sha256(table).digest() != most_common_hash:
            RNS.log(f"{RNS.prettyhexrep(peer)} sent us a corrupted or forged dns table. either way, skipping them")
            continue
        
        with open("DNS.db", "wb") as file:
            file.write(table)

        RNS.log("Got the DNS Table!!! yipeeeee (tism)")
