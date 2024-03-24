from flask import Flask, request, Response
import os
import json
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")
slack_token = os.environ.get("SLACK_BOT_TOKEN")
verification_token = os.environ.get("VERIFICATION")

slack_client = WebClient(token=slack_token)
slack_events_adapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events", app)

DATABASE_URI = f'postgresql://{os.environ.get("DB_USER")}:{os.environ.get("DB_PASSWORD")}@{os.environ.get("DB_HOST")}/testowa'
engine = create_engine(DATABASE_URI)
Session = scoped_session(sessionmaker(bind=engine))

Base = declarative_base()

class Category(Base):
    __tablename__ = 'categories'
    category_id = Column(Integer, primary_key=True)
    category_name = Column(String)

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    alias = Column(String, unique=True)
    real_name = Column(String)

class Message(Base):
    __tablename__ = 'message'
    message_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    category_id = Column(Integer, ForeignKey('categories.category_id'))
    question = Column(Text)
    date = Column(DateTime)

def init_db():
    Base.metadata.create_all(engine)

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
                                "label": {"type": "plain_text", "text": "*Screenshot URL:*"},
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
                            # Category dropdown menu
                            {
                                "type": "input",
                                "block_id": "category",
                                "element": {
                                    "type": "static_select",
                                    "placeholder": {
                                        "type": "plain_text",
                                        "text": "Select a category"
                                    },
                                    "action_id": "category_selection",
                                    "options": [
                                        {
                                            "text": {"type": "plain_text", "text": "Device location"},
                                            "value": "1"
                                        },
                                        {
                                            "text": {"type": "plain_text", "text": "Delivery"},
                                           "value": "2"
                                        },
                                    ]
                                },
                                "label": {"type": "plain_text", "text": "*Category:*"}
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
        session = Session()
        try:
            submitted_data = payload["view"]["state"]["values"]
            user_id = payload["user"]["id"]
            user_info = get_user_info(user_id)

            if user_info:
                task_name = submitted_data["task_name"]["task_name_input"]["value"]
                question = submitted_data["question"]["question_input"]["value"]
                video_url = submitted_data["video_url"]["video_url_input"]["value"]
                screenshot_url = submitted_data["screenshot_url"]["screenshot_url_input"]["value"]
                frames = submitted_data["frames_range"]["frames_range_input"]["value"]
                category_name = submitted_data["category"]["category_selection"]["selected_option"]["text"]["text"]
                category_type = submitted_data["category"]["category_selection"]["selected_option"]["value"]

                user_display = f"{user_info['real_name']} (<@{user_info['user_id']}>)"

                message_text = (
                    f"*From:* {user_display}\n"
                    f"*Task name:* {task_name}\n"
                    f"*Question:* {question}\n"
                    f"*Video URL:*\n{video_url}\n"
                    f"*Screenshot URL:*\n{screenshot_url}\n"
                    f"*Frames:* {frames}\n"
                    f"*Category:* {category_name}\n"
                )

                slack_client.chat_postMessage(channel="#test_bot", text=message_text)

                user = session.query(User).filter_by(alias=user_info['display_name']).first()
                if user is None:
                    user = User(alias=user_info['display_name'], real_name=user_info['real_name'])
                    session.add(user)
                    session.commit()

                new_message = Message(
                    date = datetime.now(),
                    user_id=user.user_id,
                    category_id=category_type,
                    question=question
                )
                session.add(new_message)
                session.commit()
        except SlackApiError as e:
            print(f"Error posting message: {e.response['error']}")
            session.rollback()
            return Response("Error"), 500
        finally:
            session.close()
    return Response(), 200

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

if __name__ == "__main__":
    init_db()
    app.run(port=3000, debug=True)

