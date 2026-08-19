import os
import json
import secrets
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, session

from . import db, auth, chat, dashboard

from .language_model import LanguageModel
from .grammar_correction import GrammarModel

load_dotenv() # Load env variables

def create_app(test_config=None):
    """ Create the application.
    """
    # create and configure the app instance
    app = Flask(__name__, instance_relative_config=True)

    # Read SECRET_KEY from env, otherwise generate and persist one so
    # sessions survive restarts.
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        secret_file = Path(app.instance_path) / 'secret_key'
        if secret_file.exists():
            secret_key = secret_file.read_text().strip()
        else:
            secret_key = secrets.token_hex(32)
            try:
                os.makedirs(app.instance_path)
                secret_file.write_text(secret_key)
            except OSError:
                pass  # fall back to a per-process secret

    app.config.from_mapping(
        SECRET_KEY=secret_key,
        DATABASE=os.path.join(app.instance_path, 'chatbot.sqlite'),
        LOAD_GRAMMAR_MODEL=True
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Ensure required environment vars exist
    # A key for either provider is required; OpenCode Zen free models also
    # work without one (rate-limited).
    missing_env_vars = []
    if not (os.getenv('OPENCODE_API_KEY') or os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')):
        missing_env_vars.append('OPENCODE_API_KEY/OPENROUTER_API_KEY/OPENAI_API_KEY')
    if not os.getenv('OPENAI_ENGINE') and not os.getenv('OPENCODE_MODEL') and not os.getenv('OPENROUTER_MODEL'):
        missing_env_vars.append('OPENCODE_MODEL')
    if missing_env_vars:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing_env_vars)}. "
            "Set them in the .env file."
        )

    # Initialize the database
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(dashboard.bp)

    # Register routes
    @app.route('/')
    def index():
        return render_template('index.html')

    # app.config['LOAD_LANGUAGE_MODEL'] = False

    app.language_model = LanguageModel()
    if app.config['LOAD_GRAMMAR_MODEL']:
        app.grammar_correction = GrammarModel(models = 1, use_gpu=False)

    # Load prompts data
    prompts_path = Path(app.root_path) / 'data' / 'prompts.json'
    with open(prompts_path, 'r', encoding='utf-8') as f:
        app.prompts = json.load(f)


    from chatbot.utils import CustomJSONProvider
    app.json_provider_class = CustomJSONProvider
    app.json = CustomJSONProvider(app)


    return app

