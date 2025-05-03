# AskDB App

**AskDB App** is a developer-friendly tool that enables users to interact with SQL databases using natural language. It combines a FastAPI backend with a Slackbot interface, allowing users to query and visualize data without writing SQL.

---

## 🚀 Features

- **Natural Language to SQL**: Convert plain English queries into SQL statements.
- **Slack Integration**: Interact with your database directly from Slack.
- **FastAPI Backend**: Robust and scalable API built with FastAPI.
- **Data Visualization**: Generate charts and graphs from query results.
- **Asynchronous Processing**: Efficient handling of multiple requests using async capabilities.

---

## 🛠️ Installation

### Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose (optional, for containerized deployment)

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/aghoba/askdb-app.git
   cd askdb-app
   ```

2. **Set Up Virtual Environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**

   Create a `.env` file in the project root with the necessary environment variables.

5. **Run the Application**

   ```bash
   uvicorn apps.api.main:app --reload
   ```

---

## 🧪 Testing

To run tests, use:

```bash
pytest
```

---

## 📂 Project Structure

```
askdb-app/
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   └── ...
│   └── slackbot/
│       ├── main.py
│       └── ...
├── data/
├── .env
├── requirements.txt
└── README.md
```

---

## 🤝 Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

---

## 📄 License

This project is licensed under the MIT License.