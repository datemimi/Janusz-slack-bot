from flask import Flask, request, Response, jsonify
import os
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

app = Flask(__name__)

# Environmental variables
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
slack_token = os.environ.get("SLACK_BOT_TOKEN")
verification_token = os.environ.get("VERIFICATION")

slack_client = WebClient(token=slack_token)
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

@app.route("/", methods=["GET", "POST"])
def event_hook():
    if request.method == "POST":
        json_dict = json.loads(request.data.decode("utf-8"))
        if json_dict["type"] == "url_verification":
            return json_dict["challenge"]
    return Response(status=200)

# @slack_events_adapter.on("message")
# def handle_message(event_data):
#     message = event_data["event"]
#     if message.get("subtype") is None:
#         text1 = message.get("text")
#         channel_id = message["channel"]

@app.route("/joke-command", methods=["POST"])
def joke_command():
    if request.form.get("token") != verification_token:
        return Response("Invalid token"), 403

    trigger_id = request.form.get("trigger_id")
    if trigger_id:
        try:
            slack_client.views_open(
                trigger_id=trigger_id,
                view={
                    "type": "modal",
                    "callback_id": "joke-modal",
                    "title": {"type": "plain_text", "text": "Joke Submission"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "task_name",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "task_name_input",
                            },
                            "label": {"type": "plain_text", "text": "Task name:"},
                        },
                        {
                            "type": "input",
                            "block_id": "question",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "question_input",
                                "multiline": True,
                            },
                            "label": {"type": "plain_text", "text": "Question:"},
                        },
                        {
                            "type": "input",
                            "block_id": "video_url",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "video_url_input",
                            },
                            "label": {"type": "plain_text", "text": "Video URL:"},
                        },
                        {
                            "type": "input",
                            "block_id": "screenshot_url",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "screenshot_url_input",
                            },
                            "label": {"type": "plain_text", "text": "Screenshot URL:"},
                        },
                        {
                            "type": "input",
                            "block_id": "frames_range",
                            "element": {
                                "type": "plain_text_input",
                                "action_id": "frames_range_input",
                            },
                            "label": {"type": "plain_text", "text": "Frames:"},
                        },
                    ],
                    "submit": {"type": "plain_text", "text": "Submit"},
                },
            )
        except SlackApiError as e:
            print(f"Error opening modal: {e.response['error']}")
            return Response("Error"), 500
    else:
        return Response("Trigger ID not provided"), 400

    return Response(), 200

@app.route("/submission", methods=["POST"])
def handle_submission():
    payload = json.loads(request.form.get("payload"))

    if payload["type"] == "view_submission":
        submitted_data = payload["view"]["state"]["values"]

        task_name = submitted_data["task_name"]["task_name_input"]["value"]
        question = submitted_data["question"]["question_input"]["value"]
        video_url = submitted_data["video_url"]["video_url_input"]["value"]
        screenshot_url = submitted_data["screenshot_url"]["screenshot_url_input"]["value"]
        frames = submitted_data["frames_range"]["frames_range_input"]["value"]

        try:
            slack_client.chat_postMessage(
                channel="#testing",
                text=f"Task name: {task_name}\nQuestion: {question}\nVideo: {video_url}\nScreenshot: {screenshot_url}\nFrames: {frames}",
            )

        except SlackApiError as e:
            print(f"Error posting message: {e.response['error']}")
            return Response("Error"), 500

    return Response(), 200

if __name__ == "__main__":
    app.run(port=3000, debug=True)
