from flask import Flask, Response, request 
import os
import json
from threading import Thread
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

app = Flask(__name__)

greetings = ["hi", "hello", "morning", "hey"]

# Ustawienie zmiennych środowiskowych
SLACK_SIGNING_SECRET = os.environ['SLACK_SIGNING_SECRET']
slack_token = os.environ['SLACK_BOT_TOKEN']

slack_client = WebClient(token=slack_token)

# Inicjalizacja SlackEventAdapter
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

# Funkcja obsługująca żądania HTTP GET/POST na głównym endpointcie
@app.route("/", methods=['GET', 'POST'])
def event_hook():
    if request.method == 'POST':
        json_dict = json.loads(request.data.decode("utf-8"))
        # Obsługa URL Verification Challenge od Slack
        if json_dict['type'] == 'url_verification':
            return json_dict['challenge']
    return Response(status=200)

# Obsługa zdarzeń typu 'app_mention', kiedy aplikacja jest wspomniana
@slack_events_adapter.on("app_mention")
def handle_message(event_data):
    message = event_data["event"]
    # Sprawdzenie, czy wiadomość nie jest subtypem innym niż standardowa wiadomość (np. wiadomość usunięta)
    if message.get("subtype") is None:
        text = message.get("text")
        channel_id = message["channel"]
        if any(greeting in text.lower() for greeting in greetings):
            try:
                response = slack_client.chat_postMessage(
                    channel=channel_id,
                    text=f"Hello <@{message['user']}>! :tada:"
                )
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")

# Uruchomienie serwera Flask
if __name__ == "__main__":
    app.run(port=3000, debug=True)
