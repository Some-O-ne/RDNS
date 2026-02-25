import os,RNS
IDENTITY_FILE_NAME = "identity"
identity = None
def getIdentity():
    global identity
    if identity != None:
        return identity

    if os.path.isfile(IDENTITY_FILE_NAME):
        try: identity = RNS.Identity.from_file(os.path.abspath(IDENTITY_FILE_NAME))
        except Exception as e: RNS.log(e)

    if not identity:
        identity = RNS.Identity()
        RNS.log("Saving identity to disk...")
        RNS.log(identity.to_file(os.path.abspath(IDENTITY_FILE_NAME)))
    return identity
