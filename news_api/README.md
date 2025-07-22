# News API

This project is a FastAPI application that provides endpoints for fetching news articles from various sources. It includes features such as retrieving today's news, searching for articles based on queries, and filtering news by categories.

## Project Structure

```
news_api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance and routes inclusion
│   ├── routers/             # All feature-based routes here
│   │   ├── __init__.py
│   │   ├── today.py         # `/today` news endpoint
│   │   ├── search.py        # `/search?q=...` endpoint
│   │   ├── categories.py    # `/category/{name}` endpoint (e.g. sports, business)
│   ├── services/            # Logic layer
│   │   ├── __init__.py
│   │   └── news_fetcher.py  # RSS fetch logic
│   ├── models/              # Pydantic models for response
│   │   └── news.py
│   ├── config.py            # Config for global constants (RSS base, lang, etc.)
├── requirements.txt
├── README.md
└── .env (optional for config)
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/news_api.git
   cd news_api
   ```

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

To run the FastAPI application, execute the following command:

```
uvicorn app.main:app --reload
```

This will start the server at `http://127.0.0.1:8000`. You can access the API documentation at `http://127.0.0.1:8000/docs`.

## Endpoints

- **GET /today**: Retrieve news articles for the current day.
- **GET /search?q={query}**: Search for news articles based on a query parameter.
- **GET /category/{name}**: Retrieve news articles based on the specified category (e.g., sports, business).

## Configuration

You can configure global constants such as the RSS base URL and language preferences in the `app/config.py` file. If you have sensitive information like API keys, consider using the `.env` file to store them securely.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.