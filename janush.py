from flask import Flask, request, Response
import os

import json

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter

from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
slack_token = os.environ.get("SLACK_BOT_TOKEN")
verification_token = os.environ.get("VERIFICATION")

slack_client = WebClient(token=slack_token)
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)


def get_user_info(user_id):
    try:
        user_info = slack_client.users_profile_get(user=user_id)
        return {
            "real_name": user_info["profile"].get("real_name_normalized", ""),
            "display_name": user_info["profile"].get("display_name_normalized", ""),
            "user_id": user_id,
        }
    except SlackApiError as e:
        print(f"Error getting user info: {e.response['error']}")
        return None


@app.route("/", methods=["GET", "POST"])
def event_hook():
    if request.method == "POST":
        json_dict = json.loads(request.data.decode("utf-8"))
        if json_dict["type"] == "url_verification":
            return json_dict["challenge"]
    return Response(status=200)


@app.route("/question", methods=["POST"])
def question_command():
    if request.form.get("token") != verification_token:
        return Response("Invalid token"), 403

    trigger_id = request.form.get("trigger_id")
    user_id = request.form.get("user_id")

    if trigger_id and user_id:
        user_info = get_user_info(user_id)
        if user_info:
            try:
                slack_client.views_open(
                    trigger_id=trigger_id,
                    view={
                        "type": "modal",
                        "callback_id": "question-modal",
                        "title": {"type": "plain_text", "text": "Your Question"},
                        "blocks": [
                            {
                                "type": "input",
                                "block_id": "task_name",
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "task_name_input",
                                },
                                "label": {"type": "plain_text", "text": "*Task name:*"},
                            },
                            {
                                "type": "input",
                                "block_id": "question",
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "question_input",
                                    "multiline": True,
                                },
                                "label": {"type": "plain_text", "text": "*Question:*"},
                            },
                            {
                                "type": "input",
                                "block_id": "video_url",
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "video_url_input",
                                    "multiline": True,
                                },
                                "label": {"type": "plain_text", "text": "*Video URL:*"},
                            },
                            {
                                "type": "input",
                                "block_id": "screenshot_url",
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "screenshot_url_input",
                                    "multiline": True,
                                },
                                "label": {
                                    "type": "plain_text",
                                    "text": "*Screenshot URL:*",
                                },
                            },
                            {
                                "type": "input",
                                "block_id": "frames_range",
                                "element": {
                                    "type": "plain_text_input",
                                    "action_id": "frames_range_input",
                                },
                                "label": {"type": "plain_text", "text": "*Frames:*"},
                            },
                        ],
                        "submit": {"type": "plain_text", "text": "Submit"},
                    },
                )
            except SlackApiError as e:
                print(f"Error opening modal: {e.response['error']}")
                return Response("Error"), 500
        else:
            return Response("User info not found"), 500
    else:
        return Response("Trigger ID or User ID not provided"), 400

    return Response(), 200


@app.route("/submission", methods=["POST"])
def handle_submission():
    payload = json.loads(request.form.get("payload"))

    if payload["type"] == "view_submission":
        submitted_data = payload["view"]["state"]["values"]
        user_id = payload["user"]["id"]
        user_info = get_user_info(user_id)

        if user_info:
            task_name = submitted_data["task_name"]["task_name_input"]["value"]
            question = submitted_data["question"]["question_input"]["value"]
            video_url = submitted_data["video_url"]["video_url_input"]["value"]
            screenshot_url = submitted_data["screenshot_url"]["screenshot_url_input"][
                "value"
            ]
            frames = submitted_data["frames_range"]["frames_range_input"]["value"]

            user_display = f"{user_info['display_name']} (<@{user_info['user_id']}>)"
            message_text = (
                f"*From:* {user_display}\n"
                f"*Task name:* {task_name}\n"
                f"*Question:* {question}\n"
                f"*Video URL:*\n{video_url}\n"
                f"*Screenshot URL:*\n{screenshot_url}\n"
                f"*Frames:* {frames}"
            )
            try:
                slack_client.chat_postMessage(channel="#testing", text=message_text)
                print("Message sent successfully!")
            except SlackApiError as e:
                print(f"Error posting message: {e.response['error']}")
                return Response("Error"), 500
        else:
            return Response("User info not found"), 500

    return Response(), 200


if __name__ == "__main__":
    app.run(port=3000, debug=True)
