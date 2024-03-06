from flask import Flask, request, Response, jsonify
import os
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

# from quip_spreadsheet.quip import QuipClient

app = Flask(__name__)
greetings = [
    "hi",
    "hello",
    "morning",
    "hey",
    "hej",
    "czesc",
    "cześć",
    "witaj",
    "dzien dobry",
    "siema",
    "dzień dobry",
    "jol",
    "joł",
]

forbidden = [
    "fuck",
    "shit",
    "kurwa",
    "chuj",
    "gówno",
    "gówniany",
    "rozwolnienie",
    "debil",
]

smoke_break = []

jokes = []

# Environmental variables
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
slack_token = os.environ["SLACK_BOT_TOKEN"]
verification_token = os.environ["VERIFICATION"]
slack_client = WebClient(token=slack_token)
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)
# QUIP_ACCESS_TOKEN = os.environ["QUIP_PERSONAL_TOKEN"] #SEpOQU1BaG5idzg=|1741212875|8E1T9LTc2oA46yxk43aLoOI0kE/S98KU5XNM8OpCBn0=
# quip_client = QuipClient("SEpOQU1BbGk2VkI=|1741214408|7Ja1fdkdjrxWRhaqmi26MCB6105BtTCwNUuAKd7fqPM=", "https://scph7502c.quip.com/")


# HTTP GET/POST non main endpoint
@app.route("/", methods=["GET", "POST"])
def event_hook():
    if request.method == "POST":
        json_dict = json.loads(request.data.decode("utf-8"))
        # URL Verification Challenge
        if json_dict["type"] == "url_verification":
            return json_dict["challenge"]
    return Response(status=200)


# 'message' events
@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    # Check if message is not other subtype than standard message (f.e. not deleted message)
    if message.get("subtype") is None:
        text1 = message.get("text")
        channel_id = message["channel"]
        # Check if message contains any forbidden word
        for forbidden_word in forbidden:
            if forbidden_word in text1.lower():
                try:
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        text=f"Watch your language, <@{message['user']}>! :rage:",
                    )
                except SlackApiError as e:
                    print(f"Error posting message: {e.response['error']}")
                break  # Stop checking for forbidden words after the first match


# 'app_mention' events
@slack_events_adapter.on("app_mention")
def handle_app_mention(event_data):
    message = event_data["event"]
    # Check if message is not other subtype than standard message (f.e. not deleted message)
    if message.get("subtype") is None:
        text = message.get("text")
        channel_id = message["channel"]
        if any(greeting in text.lower() for greeting in greetings):
            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=f"Be more attentive,<@{message['user']}>! :wat2:",
                )
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")


# Slash command
@app.route("/joke", methods=["POST"])         
def slash_joke():
    if request.form["token"] == verification_token:
        payload = {"text": "I can tell you a joke if you want"}
        return jsonify(payload)


# Quip test

# title = "My Spreadsheet"
# threads = quip_client.search_threads(title, count=1)
# spreadsheet = threads.spreadsheets[0]
# spreadsheet.load_content()

# # Wstawianie danych do arkusza kalkulacyjnego
# page = spreadsheet.get_named_page("Sheet1")
# page.update_content([
#     ["John Doe", "jdoe@gmail.com"],
#     ["Jane Doe", "jane@gmail.com"]
# ])

# Start Flask server
if __name__ == "__main__":
    app.run(port=3000, debug=True)
