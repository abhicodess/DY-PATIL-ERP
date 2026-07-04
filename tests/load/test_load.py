from locust import HttpUser, task, between, events

class ERPUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Executed when a user starts - simulates login."""
        self.client.post("/auth/login", data={
            "role": "student",
            "username": "student_test",
            "password": "password123"
        })

    @task(7)
    def view_dashboard(self):
        self.client.get("/dashboard/student_dashboard")

    @task(2)
    def view_attendance(self):
        self.client.get("/attendance/view")

    @task(1)
    def view_results(self):
        self.client.get("/results/")

@events.quitting.add_listener
def _(environment, **kw):
    if environment.stats.total.avg_response_time > 2000:
        print("Performance Threshold Exceeded: Average Response Time > 2s")
        environment.process_exit_code = 1
    if environment.stats.total.fail_ratio > 0.1:
        print("Reliability Threshold Exceeded: Error Rate > 10%")
        environment.process_exit_code = 1
