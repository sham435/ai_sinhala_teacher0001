"""
Dashboard view.
"""
from flask import Blueprint, render_template, current_app, g

from chatbot.auth import login_required
from chatbot.utils import get_activity_plot, get_practice_distribution_plot, get_user_stats

# Create a blueprint for authentication
bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/', methods=('GET',))
@login_required
def dashboard():
    """ Route for the user dashboard
    """

    fig_activity_html = get_activity_plot(g.user['id'])

    featured_prompts = {key: current_app.prompts[key] for key in
                        ['general_chat_intermediate', 'scenario_restaurant', 'lesson_vocabulary']
                        }
        
    return render_template('dashboard/dashboard.html',
                            plot=fig_activity_html,
                            featured_prompts=featured_prompts,
                            stats=get_user_stats(g.user['id'])
                            )



@bp.route('/statistics', methods=('GET',))
@login_required
def statistics():
    """ Route for the user learning center
    """

    fig_activity_html = get_activity_plot(g.user['id'])

    fig_practice_html = get_practice_distribution_plot(g.user['id'])

    # suggested_prompts = 
    suggested_prompts = {key: current_app.prompts[key] for key in
                        ['general_chat_intermediate', 'scenario_bakery', 'scenario_restaurant']
                        }
        
    return render_template('dashboard/statistics.html', 
                            plot_activity=fig_activity_html,
                            plot_grammar=fig_practice_html,
                            suggested_prompts=suggested_prompts,
                            stats=get_user_stats(g.user['id'])
                            )

