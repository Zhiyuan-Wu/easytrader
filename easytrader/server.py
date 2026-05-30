import functools
import os

from flask import Flask, jsonify, request

from . import api
from .log import logger

app = Flask(__name__)

global_store = {}

# API Key authentication
_api_key = os.environ.get("EASYTRADER_API_KEY", "")


def _check_api_key():
    """Check API Key from header or query parameter. Returns error response or None."""
    if not _api_key:
        return None
    key = request.headers.get("X-API-Key") or request.args.get("api_key", "")
    if key != _api_key:
        return jsonify({"error": "Unauthorized: invalid or missing API key"}), 401
    return None


@app.before_request
def _auth_middleware():
    if not _api_key:
        return None
    return _check_api_key()


def error_handle(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        # pylint: disable=broad-except
        except Exception as e:
            logger.exception("server error")
            message = "{}: {}".format(e.__class__, e)
            return jsonify({"error": message}), 400

    return wrapper


@app.route("/prepare", methods=["POST"])
@error_handle
def post_prepare():
    json_data = request.get_json(force=True)

    user = api.use(json_data.pop("broker"))
    user.prepare(**json_data)

    global_store["user"] = user
    return jsonify({"msg": "login success"}), 201


@app.route("/balance", methods=["GET"])
@error_handle
def get_balance():
    user = global_store["user"]
    balance = user.balance

    return jsonify(balance), 200


@app.route("/position", methods=["GET"])
@error_handle
def get_position():
    user = global_store["user"]
    position = user.position

    return jsonify(position), 200


@app.route("/auto_ipo", methods=["GET"])
@error_handle
def get_auto_ipo():
    user = global_store["user"]
    res = user.auto_ipo()

    return jsonify(res), 200


@app.route("/today_entrusts", methods=["GET"])
@error_handle
def get_today_entrusts():
    user = global_store["user"]
    today_entrusts = user.today_entrusts

    return jsonify(today_entrusts), 200


@app.route("/today_trades", methods=["GET"])
@error_handle
def get_today_trades():
    user = global_store["user"]
    today_trades = user.today_trades

    return jsonify(today_trades), 200


@app.route("/cancel_entrusts", methods=["GET"])
@error_handle
def get_cancel_entrusts():
    user = global_store["user"]
    cancel_entrusts = user.cancel_entrusts

    return jsonify(cancel_entrusts), 200


@app.route("/buy", methods=["POST"])
@error_handle
def post_buy():
    json_data = request.get_json(force=True)
    user = global_store["user"]
    res = user.buy(**json_data)

    return jsonify(res), 201


@app.route("/sell", methods=["POST"])
@error_handle
def post_sell():
    json_data = request.get_json(force=True)

    user = global_store["user"]
    res = user.sell(**json_data)

    return jsonify(res), 201


@app.route("/cancel_entrust", methods=["POST"])
@error_handle
def post_cancel_entrust():
    json_data = request.get_json(force=True)

    user = global_store["user"]
    res = user.cancel_entrust(**json_data)

    return jsonify(res), 201


@app.route("/exit", methods=["GET"])
@error_handle
def get_exit():
    user = global_store["user"]
    user.exit()

    return jsonify({"msg": "exit success"}), 200


def run(port=1430, api_key=None):
    global _api_key
    _api_key = api_key or os.environ.get("EASYTRADER_API_KEY", "")
    if not _api_key:
        logger.warning("API Key 未配置，Flask 服务无认证保护，请设置 EASYTRADER_API_KEY 环境变量")
    app.run(host="0.0.0.0", port=port)
