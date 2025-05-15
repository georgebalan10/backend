from locust import HttpUser, task, between

class AdminOnly(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        response = self.client.post("/api/login", json={
            "email": "admin@admin.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
        else:
            self.token = None
            print("❌ Admin login failed")

    @task
    def get_appointments(self):
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/api/admin/appointments", headers=headers)
