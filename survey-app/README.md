# Bodycam Survey App

web app for rating / coding body-worn cam footage

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the backend server (in one terminal):
```bash
npm run server
```

3. Start the frontend dev server (in another terminal):
```bash
npm run dev
```

4. Open your browser to the URL shown (typically `http://localhost:5173`)

## Project Structure

- `data/` - Contains all video data, narratives, and atomic facts
- `responses/` - Automatically created directory for storing user responses (one JSON file per username)
- `src/` - Vue.js frontend application
- `server.js` - Express backend API server

## Data Format

- Videos are loaded from `data/videos.csv`
- Narratives are loaded from `data/Narratives/narrative_XXX.txt`
- Atomic facts are loaded from `data/Atomic Facts/atomic_facts_XXX.txt`
- User responses are saved to `responses/{username}.json`

## Response format

Each user has their own saved file in the `responses/` directory. The file is a JSON object with the following structure:

```json
{
  "video_00": {
    "likertQuestions": [
      {
        "id": 0,
        "question": "Are all key individuals (suspect, victim, witness, officer) clearly and correctly defined and described within the report?",
        "value": "agree"
      }
      ...,
    },
    "atomicFacts": [
      {
        "id": 0,
        "fact": "The suspect was wearing a black hoodie and blue jeans.",
        "value": "accurate"
      }
      ...,
    ]
  },
  "video_01": {
    ...
  },
  ...
}
```
