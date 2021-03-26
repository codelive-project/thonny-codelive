import pyDH
import threading
import os
import random
from string import ascii_lowercase

from cryptography.fernet import Fernet
from binascii import unhexlify, b2a_base64
from paho.mqtt import client, subscribe, publish

GROUP = 16


class Crypt:
    """
    Crypt provides the high level encryption module that fits the purposes of Codelive
    """

    def __init__(self, pwd):
        """
        pwd: string password
        """
        self._dh = pyDH.DiffieHellman(GROUP)

        self._pwd_key = Fernet.generate_key()
        self._sess_key = Fernet.generate_key()
        self._sess_crypt = Fernet(self._sess_key)

        self._pwd_hash = Fernet(self._pwd_key).encrypt(bytes(pwd, "utf-8"))

        # used when the password, and diffie-hellman private keys are updated
        self._dh_lock = threading.Lock()
        self._pwd_lock = threading.Lock()

    def gen_handshake_pub(self):
        """
        Generates the public key used for the key exchange
        """
        with self._dh_lock:
            return self._dh.gen_public_key()

    def get_handshake_shared(self, other_pub):
        """
        Calculates the shared private key from the remote public key
        """
        with self._dh_lock:
            return self._dh.gen_shared_key(other_pub)

    def get_handshake_pwd_key(self, other_pub):
        """
        Generates the password key encrypted by the shared private key
        calculated from the remote public key
        """
        key = b2a_base64(unhexlify(self._dh.gen_shared_key(other_pub)))
        with self._pwd_lock:
            return Fernet(key).encrypt(self._pwd_key)

    def get_session_key(self):
        """
        Returns the session key
        """
        return self._sess_key

    def exchange_shared_key(self, broker, reply_topic, other_pub=None):

        dh = pyDH.DiffieHellman(16)
        if other_pub != None:
            publish.single(reply_topic, dh.gen_public_key, hostname=broker)
            return dh.gen_shared_key(other_pub)

        else:
            publish.single(reply_topic, dh.gen_public_key, hostname=broker)
            o_pub = subscribe.simple(reply_topic, hostname=broker)
            return dh.gen_shared_key(o_pub)

    def vaidate_pwd(self, broker, topic, pwd):
        """
        Client
            - send a authenticate request on authentication subtopic
                - Info sent:
                    - public key
            - exchange shared key
            - use shared key to encrypt pwd
            - send encrypted pwd

            - if accepted: return 0
            - if rejected: return -1
            - if timed out: return -2
        """
        reply_url = "".join([random.choice(ascii_lowercase) for _ in range(0, 32)])
        dh = pyDH.DiffieHellman(16)

        msg = {"instr": "new_auth", "pub": dh.gen_public_key(), "reply_url": reply_url}
        pass

    def authenticate(self, broker, topic, shared_key, role):
        """
        Host
            - exchage shared key
            - wait for encrypted password
            - decrypt payload
            - use private key to hash pwd
            -
            - listen to the remote person to respond with pwd key
            - comapre hashes
                - if accept: send affirm
                - if reject: send reject
        """

    def auth_pwd(self, pwd):
        pass

    def auth(self, _hash):
        """
        WARNING: Only to be used in handshakes

        Checks if the _hash matches the password hash stored in memory.
        If it does, the function updates the pwd key and hash and returns true, Returns False otherwise.
        """
        ret = self._pwd_hash == _hash
        self._update_pwd_key()
        return ret

    def encrypt(self, plaintext, key=None):
        """
        Encrypts plaintext using key (if provided) or the _sess_key
        """
        if key != None:
            return Fernet(key).encrypt(plaintext)

        return self._sess_crypt.encrypt(plaintext)

    def decrypt(self, ciphertext, key=None):
        """
        Decrypts ciphertext using key (if provided) or the _sess_key
        """
        if key != None:
            return Fernet(key).decrypt(ciphertext)
        else:
            return self._sess_crypt.decrypt(ciphertext)

    def _update_pwd_key(self):
        """
        Updates the password hash and key
        """
        with self._pwd_lock:
            pwd = Fernet(self._pwd_key).decrypt(self._pwd_hash)
            self._pwd_key = Fernet.generate_key()
            self._pwd_hash = Fernet(self._pwd_key).encrypt(pwd)

    def _replace_handshake_key(self):
        """
        Updates the DiffieHellman key
        """
        with self._dh_lock:
            self._dh = pyDH.DiffieHellman(GROUP)


if __name__ == "__main__":

    class CryptTester:
        def consturctor(self):
            print("- Testing constructor... ", end="")

            try:
                c = Crypt()
            except (TypeError):
                print("0...", end="\t")

            c = Crypt("test_pass")

            assert isinstance(c._dh, pyDH.DiffieHellman)
            assert isinstance(c._sess_crypt, Fernet)
            assert bytes("test_pass", "utf-8") == Fernet(c._pwd_key).decrypt(
                c._pwd_hash
            )
            print(" 1...\tPassed")

        def get_handshake_pub(self):
            print("- Testing get_handshake_pub... ", end="")
            c = Crypt("")
            assert c._dh.gen_public_key() == c.gen_handshake_pub()
            print("Passed")

        def get_handshake_shared(self):
            print("- Testing get_handshake_shared... ", end="")
            c = Crypt("")
            dh = pyDH.DiffieHellman(GROUP)
            c_pub = c.gen_handshake_pub()
            assert c.get_handshake_shared(dh.gen_public_key()) == dh.gen_shared_key(
                c.gen_handshake_pub()
            )
            print("Passed")

        def get_pwd_key(self):
            print("- Testing get_pwd_key... ", end="")
            c = Crypt("test_password")
            dh = pyDH.DiffieHellman(GROUP)

            dh_pub = dh.gen_public_key()
            c_pub = c.gen_handshake_pub()
            priv_key = b2a_base64(unhexlify(dh.gen_shared_key(c_pub)))

            assert priv_key == b2a_base64(unhexlify(c.get_handshake_shared(dh_pub)))
            assert c._pwd_key == Fernet(priv_key).decrypt(
                c.get_handshake_pwd_key(dh_pub)
            )
            print("Passed")

        def get_session_key(self):
            print("- Testing get_session_key... ", end="")
            c = Crypt("test_password")
            assert c.get_session_key() == c._sess_key
            print("Passed")

        def auth(self):
            print("- Testing auth... ", end="")
            c = Crypt("test_password")
            c_hash = c._pwd_hash
            c_key = c._pwd_key

            assert c.auth(c_hash)
            assert c._pwd_hash != c_hash
            assert c._pwd_key != c_key
            print("Passed")

        def encrypt(self):
            print("- Testing encrypt... ")
            c = Crypt("test_password")

            print("\t > Without key... ", end="")
            text = bytes("Test message", "utf-8")
            assert Fernet(c._sess_key).decrypt(c.encrypt(text)) == text
            print("Passed")

            print("\t > With key... ", end="")
            key = Fernet.generate_key()
            assert Fernet(key).decrypt(c.encrypt(text, key)) == text
            print("Passed")

            print("\t Passed")

        def decrypt(self):
            print("- Testing decrypt... ")
            c = Crypt("test_password")

            print("\t > Without key... ", end="")
            text = bytes("Test message", "utf-8")
            assert c.decrypt(Fernet(c._sess_key).encrypt(text)) == text
            print("Passed")

            print("\t > With key... ", end="")
            key = Fernet.generate_key()
            assert c.decrypt(Fernet(key).encrypt(text), key) == text
            print("Passed")

            print("\t Passed")

        def _update_pwd_key(self):
            print("- Testing _update_pwd_key... ", end="")

            c = Crypt("test_password")
            c_hash = c._pwd_hash
            c_key = c._pwd_key

            c._update_pwd_key()

            assert c_hash != c._pwd_hash
            assert c_key != c._pwd_key
            print("Passed")

        def _replace_handshake_key(self):
            print("- Testing _replace_handshake_key... ", end="")
            c = Crypt("test_password")
            c_dh = c._dh
            c._replace_handshake_key()
            assert c._dh != c_dh
            print("Passed")

        def all(self):
            print("\nTesting Crypt...\n")
            self.consturctor()
            self.get_handshake_pub()
            self.get_handshake_shared()
            self.get_pwd_key()
            self.get_session_key()
            self.auth()
            self.encrypt()
            self.decrypt()
            self._update_pwd_key()
            self._replace_handshake_key()
            print("\nAll Tests passed!")

    test = CryptTester()
    test.all()
