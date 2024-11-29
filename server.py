import socketserver
import threading
import sqlite3
import bcrypt
import json
import os
from datetime import datetime

CONFIG_PATH = "config.json"

def load_config(config_path):
    with open(config_path, 'r') as f:
        return json.load(f)

config = load_config(CONFIG_PATH)

DB_PATH = config['db_path']
if not os.path.exists(DB_PATH):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE users (
                username TEXT PRIMARY KEY,
                password_hash TEXT
            )
        ''')

class ChatServer(socketserver.BaseRequestHandler):
    clients = {}
    lock = threading.Lock()

    def handle(self):
        self.username = None
        self.logged_in = False
        self.send(config['welcome_message'])

        try:
            while True:
                data = self.request.recv(1024).decode('utf-8').strip()
                if not data:
                    continue
                self.process_command(data)
        except (ConnectionResetError, OSError):
            pass
        finally:
            self.disconnect()

    def send(self, message):
        self.request.sendall((message + '\n').encode('utf-8'))

    def broadcast(self, message, include_self=False):
        with self.lock:
            for client in self.clients.values():
                if client is not self or include_self:
                    client.send(message)

    def process_command(self, command):
        if command.startswith('/username '):
            self.set_username(command.split(' ', 1)[1])
        elif command.startswith('/login '):
            self.login(command.split(' ', 1)[1])
        elif command.startswith('/reg '):
            self.register(command.split(' ', 1)[1])
        elif command.startswith('/leave'):
            self.leave_chat()
        elif command.startswith('/help'):
            self.send_help()
        elif command.startswith('/list'):
            self.list_users()
        elif self.logged_in:
            self.chat(command)
        else:
            self.send("You must log in first.")

    def set_username(self, username):
        self.username = username
        self.send(f"Hello, {username}!")
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                self.send("You are registered. Please use /login <password> to login.")
            else:
                self.send("You are not registered. Please use /reg <password> to register.")

    def login(self, password):
        if not self.username:
            self.send("Set your username first using /username <username>.")
            return
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (self.username,))
            row = cursor.fetchone()
            if row and bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8')):
                self.logged_in = True
                with self.lock:
                    self.clients[self.username] = self
                self.broadcast(f"{self.username} Joined chat.", include_self=True)
            else:
                self.send("Invalid password.")

    def register(self, password):
        if not self.username:
            self.send("Set your username first using /username <username>.")
            return
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with sqlite3.connect(DB_PATH) as conn:
            try:
                conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (self.username, password_hash))
                self.send("Registered. Please use /login <password> to login.")
            except sqlite3.IntegrityError:
                self.send("Username already exists.")

    def chat(self, message):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        formatted_message = f"{timestamp}<{self.username}> {message}"
        self.broadcast(formatted_message, include_self=True)

    def leave_chat(self):
        self.broadcast(f"{self.username} Leaved chat.")
        self.disconnect()
        raise ConnectionResetError

    def list_users(self):
        users = ', '.join(self.clients.keys())
        self.send(f"Online users: {users}")

    def send_help(self):
        help_message = (
            "/username <username> - Set your username\n"
            "/login <password> - Log in to your account\n"
            "/reg <password> - Register a new account\n"
            "/leave - Leave the chat\n"
            "/list - Show online users\n"
            "/help - Show this help message"
        )
        self.send(help_message)

    def disconnect(self):
        with self.lock:
            if self.username in self.clients:
                del self.clients[self.username]
        self.request.close()

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", config['port']
    server = socketserver.ThreadingTCPServer((HOST, PORT), ChatServer)
    print(f"Server running on port {PORT}")
    server.serve_forever()