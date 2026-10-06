"""Decorate the original response; no replacement template or copied team code."""
from pathlib import Path
import re
from functools import wraps
from flask import Blueprint, jsonify, request
from .providers import DataService, ProviderError


def attach(app):
    prefix = '/_axp_semiconductor'
    if 'axsx_widgets' in app.blueprints or any(rule.rule.startswith(prefix) for rule in app.url_map.iter_rules()):
        raise RuntimeError('Extension namespace already used; stopped without changing routes')
    endpoints = [rule.endpoint for rule in app.url_map.iter_rules() if rule.rule == '/app' and 'GET' in rule.methods]
    if len(endpoints) != 1:
        raise RuntimeError('Expected exactly one existing GET /app route')
    service = DataService()
    bp = Blueprint('axsx_widgets', __name__, static_folder='static', static_url_path=prefix+'/assets')

    @bp.get(prefix+'/data/<kind>')
    def data(kind):
        if kind not in ('fx','news','weather'):
            return jsonify(status='error',code='not_found'),404
        language=request.args.get('language','ko')
        if language not in ('ko','en','ja','zh'):
            return jsonify(status='error',code='invalid_language'),400
        try:
            result=jsonify(service.get(kind,language))
            result.headers['Cache-Control']='no-store'
            return result
        except ProviderError as exc:
            return jsonify(status='error',code=exc.code,source=exc.source),503

    app.register_blueprint(bp)
    original=app.view_functions[endpoints[0]]
    app.add_url_rule(prefix+'/original', 'axsx_original_workspace', original)

    @wraps(original)
    def decorated_workspace(*args,**kwargs):
        response=app.make_response(original(*args,**kwargs))
        if response.status_code != 200 or response.mimetype != 'text/html':
            return response
        html=response.get_data(as_text=True)
        required=('id="analysis-window"','id="desktop"','id="analysis-form"','id="excel-input"','id="axp-language"')
        if any(marker not in html for marker in required):
            # Fail closed if teammates later replace the integration surface.
            raise RuntimeError('Team workspace structure changed; original files are intact. Review the additive adapter.')
        html,count=re.subn(r'(<section\b[^>]*\bid="analysis-window")',r'\1 hidden',html,count=1)
        if count != 1:
            raise RuntimeError('Cannot identify original analysis window')
        html=html.replace('<body>', '<body class="axsx-preview">',1)
        assets=(f'<link rel="stylesheet" href="{prefix}/assets/widgets.css">'
                f'<script defer src="{prefix}/assets/widget-text.js"></script>'
                f'<script defer src="{prefix}/assets/widgets.js"></script>')
        html=html.replace('</head>',assets+'</head>',1)
        fragment=(Path(__file__).parent/'templates'/'widgets.html').read_text(encoding='utf-8')
        html=html.replace('</body>',fragment+'</body>',1)
        response.set_data(html)
        return response

    app.view_functions[endpoints[0]]=decorated_workspace
    app.extensions['axsx_widgets_attached'] = True
