import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from plotly.io import to_html
import json
from json import JSONEncoder, JSONDecoder
from flask import current_app
from flask.json.provider import JSONProvider
from chatbot.chat import ChatHistory
from chatbot.db import get_db


def get_activity_plot(user_id: int):
    """ Returns a plot of the user's chat activity over the last 14 days.
    """

    db = get_db()
    rows = db.execute(
        """SELECT date(created_at) AS day, COUNT(*) AS n
           FROM chat_message
           WHERE user_id = ? AND created_at >= datetime('now', '-13 days')
           GROUP BY day""",
        (user_id,)
    ).fetchall()
    counts = {r['day']: r['n'] for r in rows}

    date_range = pd.date_range(datetime.now(timezone.utc) - timedelta(days=13), datetime.now(timezone.utc))
    data = pd.DataFrame({'date': date_range})
    data['chats'] = data['date'].dt.strftime('%Y-%m-%d').map(counts).fillna(0).astype(int)

    fig = px.bar(data, x='date', y='chats', height=300,
                labels={'chats': 'messages', 'date': ''}
                )
    fig.data[0].marker.color = '#17C3B2'
    fig.update_traces(
        hoverinfo='none',
        hovertemplate=None
    )

    fig_html = to_html(fig, full_html=False, include_plotlyjs=False, config={"displayModeBar": False})
    return fig_html


def get_practice_distribution_plot(user_id: int):
    """ Returns a donut chart of the user's messages per chat scenario.

    Returns None if the user has no recorded activity yet.
    """
    db = get_db()
    rows = db.execute(
        """SELECT scenario, COUNT(*) AS amount
           FROM chat_message
           WHERE user_id = ?
           GROUP BY scenario
           ORDER BY amount DESC""",
        (user_id,)
    ).fetchall()

    if not rows:
        return None

    prompts = current_app.prompts
    data = pd.DataFrame({
        'scenario': [prompts.get(r['scenario'], {}).get('label', r['scenario']) for r in rows],
        'amount': [r['amount'] for r in rows],
    })
    fig = px.pie(data, values='amount', names='scenario', hole=0.4,
                 color_discrete_sequence=px.colors.sequential.GnBu)

    fig.update_traces(
        hoverinfo='label+value',
        hovertemplate=None
    )

    fig_html = to_html(fig, full_html=False, include_plotlyjs=False, config={"displayModeBar": False})
    return fig_html


def get_user_stats(user_id: int):
    """ Returns real usage statistics for a user. """
    db = get_db()
    total_messages = db.execute(
        "SELECT COUNT(*) AS n FROM chat_message WHERE user_id = ?", (user_id,)
    ).fetchone()['n']
    total_chats = db.execute(
        "SELECT COUNT(DISTINCT scenario) AS n FROM chat_message WHERE user_id = ?", (user_id,)
    ).fetchone()['n']

    day_rows = db.execute(
        "SELECT DISTINCT date(created_at) AS day FROM chat_message "
        "WHERE user_id = ? ORDER BY day",
        (user_id,)
    ).fetchall()
    streak = compute_streak([r['day'] for r in day_rows])

    return {
        'total_messages': total_messages,
        'total_chats': total_chats,
        'streak': streak,
    }


def compute_streak(day_strings):
    """ Count consecutive days of activity ending today (or yesterday). """
    if not day_strings:
        return 0
    day_set = set(day_strings)
    cursor = datetime.now(timezone.utc).date()
    if cursor.isoformat() not in day_set:
        cursor = cursor - timedelta(days=1)
    streak = 0
    while cursor.isoformat() in day_set:
        streak += 1
        cursor = cursor - timedelta(days=1)
    return streak


class CustomJSONEncoder(JSONEncoder):
    """ Custom JSON encoder to encode custom objects 
    
    This is included so that the ChatHistory can be JSON-serialized,
    so that it can be saved in the flask session object (which only
    accepts jsons)
    """
    def default(self, obj):
        # return super(CustomJSONEncoder, self).defaults(obj)

        if isinstance(obj, ChatHistory):
            return obj.toJSON()
        return super(CustomJSONEncoder, self).defaults(obj)

        # return JSONEncoder.default(self, obj) # default, if not Delivery object. Caller's problem if this is not serialziable.

class CustomJSONDecoder(JSONDecoder):
    """ Custom JSON decoder to decode custom objects
    see https://github.com/pallets/flask/issues/1351
    """
    def __init__(self, *args, **kwargs):
        # JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)
        # super(CustomJSONDecoder, self).__init__(object_hook=self.object_hook, *args, **kwargs)
        super(CustomJSONDecoder, self).__init__(object_hook=self.object_hook)


    def object_hook(self, obj_json):
        # import sys
        # print(obj, file=sys.stdout)
        # return obj
    
        # if '_type' not in obj:
            # return obj
        # Transform chat history to object for processing in Python
        if 'chat_history' in obj_json.keys():
            chat_history_json = obj_json['chat_history']
            obj_json['chat_history'] = ChatHistory.fromJSON(chat_history_json)
        return obj_json


class CustomJSONProvider(JSONProvider):
    """ Flask JSON provider using the custom encoder/decoder so that
    ChatHistory objects can be stored in the session.
    """
    def dumps(self, obj, **kwargs):
        return CustomJSONEncoder(**kwargs).encode(obj)

    def loads(self, s, **kwargs):
        return CustomJSONDecoder(**kwargs).decode(s)

def get_empty_chat_history():
    """ Returns a minimal chat history """
    ch = ChatHistory(prompt_base = "The following is a conversation between a Bot and a User.", tag_bot = "Bot", tag_user = "User")
    return ch

def get_simple_chat_history():
    """ Returns a minimal chat history """
    ch = ChatHistory(prompt_base = "The following is a conversation between a Bot and a User.", tag_bot = "Bot", tag_user = "User")
    ch.add_bot_message("Hello User, how are you doing?")
    ch.add_user_message("Hi Bot! Thank you, I am doing fine. How are you?")
    return ch

def print_chat_history(chat_history: ChatHistory):
    """ Print a chat history to stdout """
    import sys
    print("-----------------\nChat History\n\n", chat_history, file=sys.stdout)
    print(f"-----------------\nChat History\n\n{chat_history.get_as_prompt_with_dialog()}", file=sys.stdout)
        