import tomlkit,os,atexit,time,threading

from nacl.signing import SigningKey
from collections import Counter
from DNSServer import Server
from netutils import syncDB

import RNS

CONFIG_FILE_NAME = "config.toml"

config = {"CONSENSUS": 2/3}

server = Server()

def config_init():
    
    global config
    if os.path.isfile(CONFIG_FILE_NAME):
        config = dict(tomlkit.load(open(CONFIG_FILE_NAME,"r")))

    if "peers" not in config or type(config["peers"]) is not tomlkit.items.Array:
        config["peers"] = []

    if config["peers"] == []: 
        RNS.log("This node is not connected to a RDNS network. Serving in isolated mode, and waiting for RDNS_READY announce")
    else:
        config["peers"] = [bytes.fromhex(peer) for peer in config["peers"]]
        syncDB(config["peers"],config["CONSENSUS"])

config_init()

def get_peers():
    return config["peers"]

votings = []

def get_voting(target):
    global votings
    for voting in votings:
        if voting["target"] == target:
            return voting

    voting = {"target":target,"votes":{}}
    votings.append(voting)

    def thread():
        nonlocal voting
        global config

        while len(voting["votes"]) < (len(config["peers"])+1)*config["CONSENSUS"]:
            time.sleep(1)

        print(voting)
        voting_result = Counter(voting["votes"].values()).most_common(1)[0]

        if voting_result[1] < (len(config["peers"])+1)*config["CONSENSUS"]:
            return

        RNS.log(f"voting result for the {RNS.prettyhexrep(target)}: {voting_result}")
        if voting_result[0] != b"Y":
            return
        if len(voting["target"]) > 16:
            server.add(voting["target"][-16:].decode(),voting["target"][0:-16].decode())
        else:
            config["peers"].append(target)


    threading.Thread(target=thread ).start()


    return voting 

def prompt_vote_response(voting):
    if "self" in voting["votes"]:
        return
    response = None
    while True:
        if len(voting["target"]) > 16:
            response = input(f"Should the {voting['target'][0:-16].decode()}={voting['target'][-16:].decode()} DNS entry be in the DB? (Y/n) ")
        else:
            response = input(f"Should {RNS.prettyhexrep(voting['target'])} be allowed to be in RDNS? (Y/n)" ).lower()
        self_vote = None
        if response in ["n","no"]:
            self_vote = b"N"
        elif response in ["y","yes",""]:
            self_vote = b"Y"
        else:
            continue
        
        voting["votes"]["self"] = self_vote
        for peer in config["peers"]:
            sendRequest(peer,"RDNS_VOTE",voting["target"]+self_vote)
        return

def RDNS_VOTE(destination_hash,data): # format: domain<-destination_hash<-vote
    if destination_hash not in config["peers"]:
        return b"Denied"
    if len(data) < 17 or len(data) > 255+17 :
        return b"Invalid vote"
    
    vote = data[-1:-2:-1]

    if vote not in [b"Y",b"N"]:
        return b"Invalid vote"
    

    peer = data[-17:-1]
    if len(data) == 17 and peer in config["peers"]: # then its peer join voiting for a peer thats already joined
        return b"Invalid vote"

    domain = data[0:-17]
    
    if server.query(domain) != None: # then its a dns add voiting for a domain that already has been added
        return

    voting = get_voting(domain+peer)

    if domain != b"":
        prompt_vote_response(voting)
    
    voting["votes"][destination_hash] = vote


def RDNS_INIT(destination_hash):

    global config
    if destination_hash in config["peers"]:
        return # that node already joined the network
    
    voting = get_voting(destination_hash)
    threading.Thread(target=prompt_vote_response,args=(voting,)).start()


def at_exit():
    global config
 
    if os.path.exists(CONFIG_FILE_NAME):
        response = input(f"Overwrite {CONFIG_FILE_NAME}? (Y/n)")
        if response.lower() not in ["","y","yes"]: return

    config["peers"] = [RNS.prettyhexrep(peer)[1:-1] for peer in config["peers"]]

    tomlkit.dump(config,open(CONFIG_FILE_NAME,"w"))

atexit.register(at_exit)

class AnnounceHandler:
    def __init__(self):
        self.aspect_filter = None
        self.connectingToRDNS = False
    def received_announce(self, destination_hash, announced_identity, app_data):
        
        if app_data != b"RDNS_READY":
            return

        global config
        if "peers" in config and config["peers"] != []: # connected, no need to reconnect
            return

        if self.connectingToRDNS:
            return
        self.connectingToRDNS = True

        response = sendRequest(destination_hash,"RDNS_GET_PEERS",None)

        if len(response)%16 != 0:
            RNS.log("Peers list is corrupted, aborting this server")
            return

        if destination_hash not in response:
            response += destination_hash
        else:
            RNS.log("Its weird that the server included themselves in the peer list, RDNS specification says against this...")
            response = input("Abandon this server? (Y/n)")
            if response.lower() in ["","y","yes"]:
                return

        
        config["peers"] = [response[i:i+16] for i in range(0,len(response),16)]

        for peer in config["peers"]:
            if peer == b"": continue

            ack = sendRequest(peer,"RDNS_INIT")
            if ack != b"Acknowledged":
                RNS.log(f"Peer {RNS.prettyhexrep(peer)} didn't acknowledge this server")


        syncDB(config["peers"],config["CONSENSUS"])

        self.connectingToRDNS = False
