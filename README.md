# Live Transcription FastAPI

This sample demonstrates interacting with the Deepgram live streaming API using FastAPI

## What is Deepgram?

[Deepgram](https://deepgram.com/) is a foundational AI company providing speech-to-text and language understanding capabilities to make data readable and actionable by human or machines.

## Sign-up to Deepgram

Before you start, it's essential to generate a Deepgram API key to use in this project. [Sign-up now for Deepgram and create an API key](https://console.deepgram.com/signup?jump=keys).

## Quickstart

#### Install dependencies

Install the project dependencies.

```bash
pip install -r requirements.txt
```

#### Edit the config file

Copy the code from `sample.env` and create a new file called `.env`. Paste in the code and enter your API key you generated in the [Deepgram console](https://console.deepgram.com/).

```env
DEEPGRAM_API_KEY='whatever-your-api-key-is'
```

#### Run the application

```bash
uvicorn main:app  --port 8000 --reload
```

## Testing

To contribute or modify pytest code, install the following dependencies:

```bash
pip install -r requirements-dev.txt
```



## Resources

- [Live Flask Starter](https://github.com/deepgram-starters/live-flask-starter/)

