from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
from contextlib import contextmanager
import time
import os
from datetime import datetime
import resource 
import random

# Inventory service for SQLite integration to read/add/take hyper
class InventoryService:
    def __init__(self, db_path='inventory.db'):
        self.db_path = db_path
        self.region = 'eu'
        self._init_db()
    
    @contextmanager
    def _get_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory
                (quantity INTEGER DEFAULT 0)
            ''')
            cursor.execute('''
                INSERT OR IGNORE INTO inventory (quantity)
                VALUES (0)
            ''')
            conn.commit()
    
    def get_inventory(self):
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT quantity FROM inventory')
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def set_inventory(self, amount):
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE inventory SET quantity = ?', (amount,))
            conn.commit()
    
    def decrement_inventory(self, amount=1):
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE inventory SET quantity = MAX(quantity - ?, 0)', (amount,))
            conn.commit()
            cursor.execute('SELECT quantity FROM inventory')
            return cursor.fetchone()[0]

# HTTP controller providing REST API
class HyperStoreHandler(BaseHTTPRequestHandler):
    inventory_service = InventoryService()

    def log_message(self, format, *args):
        # Suppress logging, otherwise all access logs are printed to console
        pass

    def _send_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

        # Track the status code in the server stats
        # TODO: Currently we have more broken connections but not real server errors
        if 200 <= status < 300:
            self.server.request_stats['2xx'] += 1
        elif 400 <= status < 500:
            self.server.request_stats['4xx'] += 1
        elif 500 <= status < 600:
            self.server.request_stats['5xx'] += 1

    def do_GET(self):
        if self.path == '/api/hyper':
            quantity = self.inventory_service.get_inventory()
            self._send_response({'quantity': quantity})
        else:
            self._send_response({'error': 'Not found'}, 404)
    
    # Set amount of hyper to defined amount
    def do_POST(self):
        if self.path == '/api/hyper':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_response({'message': 'quantity is required'}, 400)
                return

            post_data = json.loads(self.rfile.read(content_length))
            quantity = post_data.get('quantity')

            if not isinstance(quantity, int) or quantity < 0:
                self._send_response({'message': 'quantity must be a positive integer'}, 400)
                return

            self.inventory_service.set_inventory(quantity)
            self._send_response({'message': f'Quantity set successfully to {quantity} Hyper'})
        else:
            self._send_response({'error': 'Not found'}, 404)

    # Buy hyper
    def do_PUT(self):
        if self.path == '/api/hyper/own':
            quantity = self.inventory_service.get_inventory()
            
            if quantity > 0:
                self.inventory_service.decrement_inventory()
                self._send_response({'message': 'Hyper acquired successfully'})
            else:
                self._send_response({'message': 'No Hyper available for you'}, 404)
        else:
            self._send_response({'error': 'Not found'}, 404)

# Start HTTP server but also print status information to console, basically 
# preventing screen burn-in but also display helpful stuff
class StatsHTTPServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_stats_time = 0
        # Track different status code ranges
        self.request_stats = {
            '2xx': 0,  # Success (200-299)
            '4xx': 0,  # Client errors (400-499)
            '5xx': 0   # Server errors (500-599)
        }

    def service_actions(self):
        current_time = time.time()
        if current_time - self.last_stats_time >= 10:
            try:
                # Get memory usage in MB
                # CPU unfortunately would require psutil which is only available on Pro edition
                mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
                mem_status = f"Memory Usage: {mem_usage:.1f}MB"
            except:
                mem_status = "Memory: N/A"
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_requests = sum(self.request_stats.values())
            stats = f"2xx: {self.request_stats['2xx']}, 4xx: {self.request_stats['4xx']}, 5xx: {self.request_stats['5xx']}"
            print(f"\r[{timestamp}] {mem_status} | Requests ({total_requests}): {stats}", end='', flush=True)
            self.last_stats_time = current_time
    
    def process_request(self, request, client_address):
        return super().process_request(request, client_address)

def run_server():
    # TODO: Random server port needed since stopping previous process is not trivial
    port = random.randint(8000, 8500)
    server_address = ('', port)
    httpd = StatsHTTPServer(server_address, HyperStoreHandler)
    print(f'Starting server on port {port}...')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == '__main__':
    run_server()