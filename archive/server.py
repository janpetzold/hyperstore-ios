from http.server import BaseHTTPRequestHandler, HTTPServer
import datetime
import json
import os
import platform
import shutil

# Function to get CPU load
def get_cpu_load():
    if shutil.which("uptime"):
        # Use `uptime` command if available
        uptime_output = os.popen("uptime").read()
        load_index = uptime_output.rfind("load averages: ")
        if load_index != -1:
            return uptime_output[load_index + 15:].strip()
    return "N/A"

# Function to get memory usage
def get_memory_usage():
    if shutil.which("vm_stat"):
        # Use `vm_stat` command on macOS/iOS
        vm_stat = os.popen("vm_stat").read()
        pages_free = int(vm_stat.split("Pages free:")[1].split(".")[0].strip())
        pages_used = int(vm_stat.split("Pages active:")[1].split(".")[0].strip())
        total_pages = pages_free + pages_used
        memory_percent = (pages_used / total_pages) * 100 if total_pages > 0 else 0
        return f"{memory_percent:.2f}%"
    return "N/A"

# Function to get battery status (iOS-specific)
def get_battery_status():
    return "Battery info not available"

# Define the request handler
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Get system metrics
        current_time = datetime.datetime.now().isoformat()
        cpu_load = get_cpu_load()
        memory_usage = get_memory_usage()
        battery_remaining = get_battery_status()

        # Create the response data
        response_data = {
            "current_time": current_time,
            "cpu_load": cpu_load,
            "memory_usage": memory_usage,
            "battery_remaining": battery_remaining
        }

        # Respond with JSON data
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_data).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress server logging to console
        return

# Run the server
def run(server_class=HTTPServer, handler_class=SimpleHandler, port=8000):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    # Run the server
    run()
