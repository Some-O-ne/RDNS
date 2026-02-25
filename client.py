import argparse
import RNS
import time
import sys
##########################################################
#### Client Part #########################################
##########################################################

# A reference to the server link
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
    return server_link

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
        "RDNS_SERVER",
        data = path.encode()+data,
        response_callback = got_response,
        failed_callback = request_failed
    )

    if not should_quit and not response:
        time.sleep(0.1)
    return response


# This initialisation is executed when the users chooses
# to run as a client.
def client(destination_hexhash, configpath):
    # We need a binary representation of the destination
    # hash that was entered on the command line
    if type(destination_hexhash) == bytes:
        destination_hash = destination_hexhash
    else:
        try:
            dest_len = (RNS.Reticulum.TRUNCATED_HASHLENGTH//8)*2
            if len(destination_hexhash) != dest_len:
                raise ValueError(
                    "Destination length is invalid, must be {hex} hexadecimal characters ({byte} bytes).".format(hex=dest_len, byte=dest_len//2)
                )
                
            destination_hash = bytes.fromhex(destination_hexhash)
        except:
            RNS.log("Invalid destination entered. Check your input!\n")
            sys.exit(0)

    # We must first initialise Reticulum
    reticulum = RNS.Reticulum(configpath)

    # Check if we know a path to the destination
    if not RNS.Transport.has_path(destination_hash):
        RNS.log("Destination is not yet known. Requesting path and waiting for announce to arrive...")
        RNS.Transport.request_path(destination_hash)
        while not RNS.Transport.has_path(destination_hash):
            time.sleep(0.1)

    # Recall the server identity
    server_identity = RNS.Identity.recall(destination_hash)
    print(server_identity)
    # Inform the user that we'll begin connecting
    RNS.log("Establishing link with server...")

    # When the server identity is known, we set
    # up a destination
    server_destination = RNS.Destination(
        server_identity,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "RDNS_SERVER",
        "RDNS_SERVER"
    )
    server_link = establish_link(server_destination)

    while not server_link:
        print("Couldn't connect to the server, retrying...")
        server_link = establish_link(server_destination)

    response = request(server_link,"RDNS_QUERY",b"iso.world")
    print(response)
    client_loop(server_link)

def client_loop(server_link):

    should_quit = False
    while not should_quit:
        try:
            print("> ", end=" ")
            text = input()

            # Check if we should quit the example
            if text == "quit" or text == "q" or text == "exit":
                should_quit = True
                server_link.teardown()
            else:
                server_link.request(
                    "RDNS_SERVER",
                    data = b"RDNS_QUERYiso.world",
                    response_callback = got_response,
                    failed_callback = request_failed
                )
            
        except Exception as e:
            RNS.log("Error while sending request over the link: "+str(e))
            should_quit = True
            server_link.teardown()

def got_response(request_receipt):
    request_id = request_receipt.request_id
    response = request_receipt.response

    RNS.log("Got response for request "+RNS.prettyhexrep(request_id)+": "+str(response))

def request_received(request_receipt):
    RNS.log("The request "+RNS.prettyhexrep(request_receipt.request_id)+" was received by the remote peer.")

def request_failed(request_receipt):
    RNS.log("The request "+RNS.prettyhexrep(request_receipt.request_id)+" failed.")


# This function is called when a link
# has been established with the server
def link_established(link):
    # We store a reference to the link
    # instance for later use
    global server_link
    server_link = link

    # Inform the user that the server is
    # connected
    RNS.log("Link established with server, hit enter to perform a request, or type in \"quit\" to quit")

# When a link is closed, we'll inform the
# user, and exit the program
def link_closed(link):
    if link.teardown_reason == RNS.Link.TIMEOUT:
        RNS.log("The link timed out, exiting now")
    elif link.teardown_reason == RNS.Link.DESTINATION_CLOSED:
        RNS.log("The link was closed by the server, exiting now")
    else:
        RNS.log("Link closed, exiting now")
    
    time.sleep(1.5)
    sys.exit(0)


##########################################################
#### Program Startup #####################################
##########################################################

# This part of the program runs at startup,
# and parses input of from the user, and then
# starts up the desired program mode.
if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Simple request/response example")

        parser.add_argument(
            "-s",
            "--server",
            action="store_true",
            help="wait for incoming requests from clients"
        )

        parser.add_argument(
            "--config",
            action="store",
            default=None,
            help="path to alternative Reticulum config directory",
            type=str
        )

        parser.add_argument(
            "destination",
            nargs="?",
            default=None,
            help="hexadecimal hash of the server destination",
            type=str
        )

        args = parser.parse_args()

        if args.config:
            configarg = args.config
        else:
            configarg = None

        if args.server:
            server(configarg)
        else:
            if (args.destination == None):
                

                print("")
                parser.print_help()
                print("")
            else:
                client(args.destination, configarg)

    except KeyboardInterrupt:
        print("")
        sys.exit(0)