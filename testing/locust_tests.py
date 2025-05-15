# -----------------------------
# Locust Test: Flow Complet - Utilizator Normal (final complet)
# -----------------------------

from locust import HttpUser, task, between
import random

class NormalUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def simulate_user_flow(self):
        # 1️⃣ Generează un email unic la fiecare sesiune
        email = f"testuser_{random.randint(10000,99999)}@example.com"
        password = "password123"

        # 2️⃣ Înregistrează user-ul
        register_response = self.client.post("/api/register", json={
            "name": "Test User",
            "email": email,
            "password": password
        })

        if register_response.status_code == 200:
            # 3️⃣ Autentificare user
            login_response = self.client.post("/api/login", json={
                "email": email,
                "password": password
            })

            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                headers = {"Authorization": f"Bearer {token}"}

                # 4️⃣ Face o rezervare
                self.client.post("/api/appointments", json={
                    "user_id": 1,
                    "date": "2025-05-15",
                    "time": "10:00",
                    "service": "Acupunctura spate"
                }, headers=headers)

                # 5️⃣ Trimite o recenzie
                self.client.post("/api/reviews", json={
                    "user_id": 1,
                    "text": "Serviciu excelent!",
                    "rating": 5
                }, headers=headers)

                # 6️⃣ Pune o întrebare la AI
                self.client.post("/api/chatbot", json={
                    "question": "Ce beneficii are acupunctura?"
                })

            else:
                print(f"❌ Login failed pentru {email}")

        else:
            print(f"❌ Register failed pentru {email}")


# -----------------------------
# Locust Test: Flow Complet - Admin (final complet)
# -----------------------------

class AdminUser(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        response = self.client.post("/api/login", json={
            "email": "admin@example.com",
            "password": "adminpassword"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
        else:
            self.token = None
            print("❌ Admin login failed")

    @task
    def admin_tasks(self):
        if hasattr(self, 'token') and self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.get("/api/admin/appointments", headers=headers)
            self.client.get("/api/admin/reviews", headers=headers)
            self.client.get("/api/admin/ai-question-stats", headers=headers)
            self.client.post("/api/admin/rebuild-index", headers=headers)
            self.client.post("/api/admin/reset-ai-questions", headers=headers)
        else:
            print("⚠️ Admin token missing - sar testele")
