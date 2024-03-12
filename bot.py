from flask import Flask, request, Response, jsonify 
import os
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

app = Flask(__name__)
greetings = [
    "hi", "hello", "morning", "hey", "hej", "czesc", "cześć", "witaj", "dzien dobry",
    "siema", "dzień dobry", "jol", "joł",
]

#forbidden = []

smoke_break = []
jokes = []

# Environmental variables
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
slack_token = os.environ["SLACK_BOT_TOKEN"]
verification_token = os.environ["VERIFICATION"]
slack_client = WebClient(token=slack_token)
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

@app.route("/", methods=["GET", "POST"])
def event_hook():
    if request.method == "POST":
        json_dict = json.loads(request.data.decode("utf-8"))
        if json_dict["type"] == "url_verification":
            return json_dict["challenge"]
    return Response(status=200)

@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    if message.get("subtype") is None:
        text1 = message.get("text")
        channel_id = message["channel"]
        for forbidden_word in forbidden:
            if forbidden_word in text1.lower():
                try:
                    slack_client.chat_postMessage(
                        channel=channel_id,
                        text=f"Watch your language, <@{message['user']}>! :rage:",
                    )
                except SlackApiError as e:
                    print(f"Error posting message: {e.response['error']}")
                break

@slack_events_adapter.on("app_mention")
def handle_app_mention(event_data):
    message = event_data["event"]
    if message.get("subtype") is None:
        text = message.get("text")
        channel_id = message["channel"]
        if any(greeting in text.lower() for greeting in greetings):
            try:
                slack_client.chat_postMessage(
                    channel=channel_id,
                    text=f"Be more attentive, <@{message['user']}>! :wat2:",
                )
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")

@app.route("/joke", methods=["POST"])
def handle_joke():
    if request.form["token"] != verification_token:
        return Response("Invalid token"), 403
    try:
        response = slack_client.views_open(
            trigger_id=request.form["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "joke-modal",
                "title": {"type": "plain_text", "text": "Wprowadź dane"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "joke_input",
                        "element": {"type": "plain_text_input", "action_id": "joke"},
                        "label": {"type": "plain_text", "text": "Video ID:"},
                    }
                ],
                "submit": {"type": "plain_text", "text": "Submit"},
            },
        )
    except SlackApiError as e:
        print(f"Error opening modal: {e.response['error']}")
        return Response("Error"), 500

    return Response(), 200

@app.route("/submission", methods=["POST"])
def handle_submission():
    payload = json.loads(request.form.get("payload"))
    if payload["type"] == "view_submission":
        submitted_data = payload["view"]["state"]["values"]
        joke_text = submitted_data["joke_input"]["joke"]["value"]
        try:
            slack_client.chat_postMessage(
                channel="#test_bot",
                text=f"Video ID: {joke_text}",
            )
        except SlackApiError as e:
            print(f"Error posting message: {e.response['error']}")
            return Response("Error"), 500

    return Response(), 200

if __name__ == "__main__":
    app.run(port=3000, debug=True)
