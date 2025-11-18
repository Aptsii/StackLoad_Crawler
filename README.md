
# Tech Stack Information Service

This project provides information about various development tech stacks in a clean, structured JSON format.

## Project Structure

- `index.html`: A web page to display the tech stack information. It fetches data from `stacks.json` and renders it as a series of cards.
- `stacks.json`: A JSON file containing the curated list of tech stacks and their detailed information.
- `api/main.py`: A FastAPI application that serves the `stacks.json` data via a `/api/stacks` endpoint.
- `README.md`: This file.

## How to Use

### Frontend

Simply open the `index.html` file in a web browser to see the list of tech stacks.

### Backend

1.  **Install dependencies:**

    ```bash
    pip install fastapi uvicorn
    ```

2.  **Run the server:**

    ```bash
    uvicorn api.main:app --reload
    ```

    The API will be available at `http://127.0.0.1:8000`.

## Tech Stack Data Format

Each tech stack object in `stacks.json` follows this structure:

```json
{
  "name": "string",
  "slug": "string",
  "category": "string",
  "description": "string",
  "logoUrl": "string (url)",
  "popularity": "number",
  "aiExplanation": "string",
  "homepage": "string (url)",
  "repo": "string (url)",
  "projectSuitability": [
    "string"
  ],
  "learningDifficulty": {
    "stars": [
      "boolean"
    ],
    "label": "string",
    "description": "string"
  }
}
```
