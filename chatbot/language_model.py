import os
import requests

from chatbot.chat import ChatHistory


class LanguageModel():
    """ Language Generation Model backed by OpenRouter (free models).
    """

    def __init__(self):
        # OpenCode Zen is the default provider; OpenRouter is used if only
        # an OpenRouter key is configured.
        self.zen_key = os.getenv("OPENCODE_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.model = (
            os.getenv("OPENCODE_MODEL", "")
            or os.getenv("OPENROUTER_MODEL", "")
            or "deepseek-v4-flash-free"
        )
        self.temperature = 0.5
        self.max_tokens = 120

        if self.openrouter_key and not self.zen_key:
            self.base_url = "https://openrouter.ai/api/v1/chat/completions"
            self.api_key = self.openrouter_key
        else:
            self.base_url = "https://opencode.ai/zen/v1/chat/completions"
            self.api_key = self.zen_key

    def add_response_to_chat_history(self, chat_history: ChatHistory):
        """ Generate a response from the bot and append to chat history.
        """
        reply_raw_text = self.get_response_from_GPT3(chat_history)

        reply_text = self.clean_reply_text(reply_raw_text,
                                        tag_bot = chat_history.tag_bot,
                                        tag_user = chat_history.tag_user
                                        )

        if reply_text:
            chat_history.add_bot_message(reply_text)
        return chat_history

    def build_messages(self, chat_history: ChatHistory):
        """ Convert the chat history into chat-completion messages.
        """
        messages = [{"role": "system", "content": chat_history.prompt_base}]
        for message in chat_history.messages:
            if message.correction:
                continue
            role = "user" if message.sender == "user" else "assistant"
            messages.append({"role": role, "content": message.text})
        return messages

    def get_response_from_GPT3(self, chat_history):
        """ Get a reply from the language model via OpenRouter.

        Returns:
        --------
         - reply: str
            A text string containing just the reply from the model.
            Example: "I'm fine, how are you?"
        """
        if not self.api_key:
            return "I can't respond right now - no OPENCODE_API_KEY is configured."

        payload = {
            "model": self.model,
            "messages": self.build_messages(chat_history),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=60)
        except requests.RequestException as exc:
            return f"I couldn't reach the model service right now: {exc}"

        if response.status_code != 200:
            detail = "unknown error"
            try:
                detail = response.json().get('error', {}).get('message', detail)
            except ValueError:
                detail = response.text[:200]
            return f"The model service returned an error: {detail}"

        data = response.json()
        choices = data.get('choices', [])
        if choices:
            return choices[0]['message']['content']

        return ''

    def clean_reply_text(self, reply_raw, tag_bot, tag_user):
        " Clean up the reply reply_raw a bit "

        reply = reply_raw.strip()

        # Remove new line characters
        reply = reply.replace(f"\n", "")

        # Get rid of "Bot: " at beginning of message
        reply = reply.replace(f"{tag_bot}: ", "")
        reply = reply.replace(f"{tag_bot}: ".lower(), "")

        # Sometimes, a partial reply of a user is included. Stop answer there
        # Example: "Bot: Hello, how are you? User: "
        if f'{tag_user}:' in reply:
            idx = reply.find(f'{tag_user}:')
            reply = reply[:idx].strip()

        return reply