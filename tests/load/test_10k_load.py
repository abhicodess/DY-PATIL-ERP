from locust import HttpUser, task, between, SequentialTaskSet
import random

# =========================================================================
# LOCUST LOAD TEST SCENARIO
# Target Workload: 10,000 concurrent students
# Weight Distribution: 70% Students, 25% Faculty, 5% Admins
# =========================================================================

class StudentBehavior(SequentialTaskSet):
    def on_start(self):
        """Simulate student login on start."""
        # Use credentials from seed data or random values
        self.username = f"student_{random.randint(1, 100)}@dypatil.edu"
        self.password = "password123"
        
        # Step 1: Login
        response = self.client.post("/api/v1/auth/login", json={
            "username": self.username,
            "password": self.password,
            "role": "student"
        })
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
        
    @task
    def view_attendance(self):
        """Simulate viewing cumulative attendance and history logs."""
        self.client.get("/api/v1/student/attendance")

    @task
    def view_results(self):
        """Simulate viewing marksheet and published grades."""
        self.client.get("/api/v1/student/results")


class FacultyBehavior(SequentialTaskSet):
    def on_start(self):
        """Simulate faculty login on start."""
        self.username = f"faculty_{random.randint(1, 20)}@dypatil.edu"
        self.password = "password123"
        
        response = self.client.post("/api/v1/auth/login", json={
            "username": self.username,
            "password": self.password,
            "role": "faculty"
        })
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task
    def view_timetable(self):
        """Simulate viewing today's lecture timetable."""
        # Call the faculty timetable endpoint (e.g. /api/v1/faculty/timetable or dashboard info)
        self.client.get("/api/v1/dashboard/summary")

    @task
    def submit_attendance(self):
        """Simulate taking and submitting student attendance."""
        # First initialize the session for timetable slot
        init_res = self.client.post("/api/v1/attendance/session/initialize", json={
            "timetable_id": random.randint(1, 10)
        })
        
        if init_res.status_code == 200:
            session_id = init_res.json().get("data", {}).get("session_id")
            students = init_res.json().get("data", {}).get("students", [])
            
            # Formulate present/absent logs
            records = []
            for s in students:
                records.append({
                    "student_id": s["id"],
                    "status": "Present" if random.random() > 0.1 else "Absent"
                })
                
            # Submit final attendance session
            self.client.post(
                f"/api/v1/attendance/submit?is_final=true", 
                json={
                    "session_id": session_id,
                    "records": records
                }
            )


class AdminBehavior(SequentialTaskSet):
    def on_start(self):
        """Simulate admin login on start."""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123",
            "role": "admin"
        })
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task
    def view_dashboard_stats(self):
        """Simulate viewing consolidated statistics (scraped/cached queries)."""
        self.client.get("/api/v1/dashboard/summary")

    @task
    def view_student_list(self):
        """Simulate searching and filtering students."""
        self.client.get("/api/v1/attendance?dept=AIML&division=A")


# =========================================================================
# Locust User Definitions with Weights and Browse Pacing
# =========================================================================

class StudentUser(HttpUser):
    weight = 70
    tasks = [StudentBehavior]
    # Realistic wait time between student queries (30s to 120s)
    wait_time = between(30, 120)


class FacultyUser(HttpUser):
    weight = 25
    tasks = [FacultyBehavior]
    # Faculty performs submissions every 2 minutes (120s)
    wait_time = between(100, 140)


class AdminUser(HttpUser):
    weight = 5
    tasks = [AdminBehavior]
    # Admins browse less frequently (60s to 180s)
    wait_time = between(60, 180)
