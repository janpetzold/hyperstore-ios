import random
import os
from locust import HttpUser, task, between, SequentialTaskSet

class HyperstoreUserBehavior(SequentialTaskSet):
    wait_time = between(1, 2)  # Delay between 1-2 seconds for each task

    @task
    def read_hyper(self):
        """Step 1: Call the GET endpoint 5-12 times."""
        for _ in range(random.randint(5, 12)):
            with self.client.get("/api/hyper", catch_response=True) as response:
                if response.status_code == 401:
                    response.failure(f"Could not read hyper due to authentication - access token: {self.read_access_token}")
                elif response.status_code != 200:
                    response.failure(f"Could not read hyper. Status code: {response.status_code}, Response: {response.text}")
            self.wait()

    @task
    def buy_hyper(self):
        """Step 2: Call the buy endpoint a few times."""
        for _ in range(random.randint(1, 3)):
            with self.client.put("/api/hyper/own", catch_response=True) as response:
                if response.status_code != 200:
                    response.failure("Could not buy hyper")
            self.wait()
    
    @task
    def read_hyper_again(self):
        """Step 3: Read hyper amount again"""
        for _ in range(random.randint(2, 5)):
            with self.client.get("/api/hyper", catch_response=True) as response:
                if response.status_code == 401:
                    response.failure(f"Could not read hyper due to authentication - access token: {self.read_access_token}")
                elif response.status_code != 200:
                    response.failure(f"Could not read hyper again. Status code: {response.status_code}, Response: {response.text}")
            self.wait()

    @task
    def post_endpoint_call_few_times(self):
        """Step 4: Reset stock to 200 hyper"""
        with self.client.post("/api/hyper", json={"quantity": 200}, catch_response=True) as response:
            if response.status_code != 200:
                response.failure("Failed to set quantity to 200")
        self.wait()
        
        # Finish the sequence
        self.interrupt()  # Stop the user after completing the sequence

class HyperstoreUser(HttpUser):
    tasks = [HyperstoreUserBehavior]