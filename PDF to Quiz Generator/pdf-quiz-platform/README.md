# 📄➡️❓ PDF to Quiz Generator

An end-to-end **PDF to Quiz Generation Platform** built with **FastAPI**, **PostgreSQL**, **Redis**, **Docker**, and **Nginx**. The system ingests PDFs, processes and chunks content, applies AI/NLP pipelines, and generates quizzes automatically.

---

## 🚀 Tech Stack

* **Backend**: Python 3.11, FastAPI
* **AI / NLP**: Transformers, Sentence Transformers
* **Database**: PostgreSQL 15
* **Cache / Queue**: Redis 7
* **Reverse Proxy**: Nginx
* **Containerization**: Docker & Docker Compose

---

## 📁 Project Structure

```text
pdf-quiz-platform/
│
├── backend/
│   ├── app.py
│   ├── main.py
│   ├── requirements.txt
│   ├── api/
│   ├── core/
│   ├── services/
│   ├── db/
│   └── config/
│
├── frontend/
│   └── (static files served by nginx)
│
├── docker/
│   ├── docker-compose.yml
│   ├── backend.Dockerfile
│   ├── nginx.Dockerfile
│   └── nginx.conf
│
├── data/
│   ├── uploads/
│   ├── processed/
│   ├── chunks/
│   ├── quizzes/
│   └── vector_index/
│
├── .env
└── README.md
```

---

## 🔐 Environment Variables

Create a `.env` file **inside the `docker/` directory**:

```env
# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

# JWT
JWT_SECRET_KEY=super-secret-jwt-key-change-this
```

> ⚠️ **Never commit `.env` to Git**

---

## 🔑 How to Get Keys

### OpenAI API Key

1. Go to: [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)
2. Create a new secret key
3. Copy and paste it into `.env`

### JWT Secret Key

Generate locally:

```bash
openssl rand -hex 32
```

---

## 🐳 Running with Docker

### 1️⃣ Stop Existing Containers (Clean Start)

```bash
docker compose down -v
```

### 2️⃣ Build & Start Services

```bash
docker compose up --build
```

---

## 🌐 Service Ports

| Service     | Port     |
| ----------- | -------- |
| Backend API | **8080** |
| PostgreSQL  | 5432     |
| Redis       | 6379     |
| Nginx       | 81 / 443 |

Backend will be available at:

👉 **[http://localhost:8080](http://localhost:8080)**

---

## 🧪 Health Checks

* PostgreSQL: `pg_isready`
* Redis: `redis-cli ping`
* Backend starts only after DB & Redis are healthy

---

## 🛠 Common Issues & Fixes

### ❌ `Counter is not defined`

Fix in `core/deduplication.py`:

```python
from collections import Counter
```

---

### ❌ Port Already in Use

If port **8080** is busy:

```bash
lsof -i :8080
kill -9 <PID>
```

---

### ❌ Database Connection Issues

Ensure DATABASE_URL:

```text
postgresql://quizadmin:quizpassword@postgres:5432/quizdb
```

---

## 📦 Rebuilding Only Backend

```bash
docker compose build backend
docker compose up backend

docker compose down -v
docker compose up --build

```

---

## 📜 Logs

```bash
docker compose logs -f backend
docker compose logs -f postgres
docker compose logs -f redis
```

---

## ✅ Production Notes

* Use `.env.production`
* Rotate JWT secrets
* Add HTTPS certs to Nginx
* Persist vector indexes properly

---

## 👨‍💻 Author

**Faadil**

---

## ⭐ Ready to Go

Your PDF → Quiz pipeline is now fully containerized and production-ready 🚀
