import random

# "Proof of concept" 'salt & pepper'ed password hash. A string is formed by concatenating a randomly generated per-user 'salt', the user's name, the user's password, and an env var 'pepper'.
# Not actually secure for real use, but just a fun thing to model.

#Stores a dict of Password objects (username, salt, hash)
#   Useful for ensuring no duplicate usernames
#   Future implementation: Automatically store and retrieve dict to file for data persistence so client doesn't have to
class PasswordManager():
    
    def __init__(self, file_path: str = None):
        #self.passwords is a dict of usernames and Password objects
        self.passwords = {};
    
    def add(self, username, password):
        if username in self.passwords.keys():
            raise KeyError("Cannot add duplicate usernames");
        
        self.passwords[username] = Password(username, password);
        
    #Returns true if username & password combo is valid 
    def validate(self, username, candidate) -> bool:
        if not username in self.passwords.keys():
            return False;
        return self.passwords[username].validate(candidate);
        
    def contains(self, username) -> bool:
        return username in self.passwords.keys();
    
    def __str__(self):
        res = "";
        for password in self.passwords.values():
            res += str(password) + "\n";
        return res;

#Contains exactly one username, its random salt, and its hash.
#Password is not contained.
class Password():
    def __init__(self, username: str, password: str):
        salt = "";
        chars = "!@#$%^&*abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i in range(8):
            salt += random.choice(chars);
            
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        # Always load .env from the same directory as this file
        load_dotenv(Path(__file__).resolve().parent / ".env")
        pepper = os.environ["PEPPER"] 
        
        hash_code = hex(Password.hash_me(salt + username + password + pepper));
        
        self.username = username;
        self.salt = salt;
        self.hash_code = hash_code;
    
    #Returns true if password candidate matches this Password object's hash
    def validate(self, user, candidate, correct_hash) -> bool:
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        # Always load .env from the same directory as this file
        load_dotenv(Path(__file__).resolve().parent / ".env")
        pepper = os.environ["PEPPER"] 
        
        if hex(Password.hash_me(self.salt + candidate + pepper)) == self.hash_code:
            return True;
        return False;
    
    def hash_me(str) -> int:  
        # print(str);      
        res = len(str);
        # print(res);
        for c in str:
            res += (res * 13 + ord(c) * 7);
            res %= 2**32
            # print(res);
        return res
    
    def __str__(self):
        return self.username + "," + self.salt + "," + str(self.hash_code);
