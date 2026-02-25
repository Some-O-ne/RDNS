
import sqlite3,hashlib,os,time
from functools import lru_cache
@lru_cache(maxsize=None)
class Server:
    def __init__(self):
        self.connection = sqlite3.Connection("DNS.db",check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS dns (
                                domain TEXT PRIMARY KEY,
                                address CHAR(32)
                            );
        ''')
        self.connection.commit()
        self.computing_hash = False
        self.hash = self.compute_db_hash()

    def query(self,domain:str)->str|None:
        result = self.cursor.execute("SELECT address FROM dns WHERE domain=?",(domain,))
        addr = result.fetchone()
        if not addr:
            return None
        return addr[0]
    
    def add(self,address:str,domain:str):
        self.cursor.execute("INSERT INTO dns VALUES (?,?)",(domain,address,))
        self.connection.commit()
        self.hash = self.compute_db_hash()
    
    def get_db_hash(self):
        while self.computing_hash:
            time.sleep(0.1)
        return self.hash

    def get_db(self):
        return open("DNS.db","rb").read()
    def compute_db_hash(self):
        self.computing_hash = True
        db = open("DNS.db","rb")

        hashobj = hashlib.sha256()
        chunk = None
        while chunk != b"":
            chunk = db.read(65535)
            hashobj.update(chunk)

        self.computing_hash = False

        db.close()
        return hashobj.digest()
