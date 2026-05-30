import functools
import os

from flask import Flask, jsonify, request

from . import api
from . import exceptions
from .log import logger

app = Flask(__name__)

# 配置 Flask 的 JSON 编码器
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

global_store = {}

# 确保启动时客户端处于打开状态，dummy prepare，且76行跳过准备
user = api.use('universal_client')
user.prepare(user="1", password="1", exe_path=r"C:\同花顺软件\同花顺\xiadan.exe")
global_store["user"] = user

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


def _get_user():
    """Get the logged-in trader instance. Returns (user, None) or (None, error_response)."""
    user = global_store.get("user")
    if user is None:
        return None, (jsonify({"error": "请先调用 POST /prepare 登录券商客户端"}), 403)
    return user, None


def error_handle(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exceptions.TradeError as e:
            logger.warning("trade error: %s", e)
            return jsonify({"error": str(e)}), 409
        except KeyError as e:
            logger.warning("missing parameter: %s", e)
            return jsonify({"error": "缺少必要参数: {}".format(e)}), 422
        except (TypeError, ValueError) as e:
            logger.warning("invalid parameter: %s", e)
            return jsonify({"error": "参数错误: {}".format(e)}), 422
        except NotImplementedError as e:
            logger.warning("not implemented: %s", e)
            return jsonify({"error": "不支持的券商类型或操作"}), 400
        except Exception as e:
            logger.exception("server error")
            message = "{}: {}".format(e.__class__.__name__, e)
            return jsonify({"error": message}), 500

    return wrapper


@app.route("/prepare", methods=["POST"])
@error_handle
def post_prepare():
    if "user" in global_store:
        return jsonify({"msg": "login success"}), 201
    
    json_data = request.get_json(force=True)

    if "broker" not in json_data:
        return jsonify({"error": "缺少必要参数: broker"}), 422

    # 服务端环境变量预设默认值，客户端参数优先
    if "exe_path" not in json_data and os.environ.get("EXE_PATH", "").strip():
        json_data["exe_path"] = os.environ["EXE_PATH"]
    if "comm_password" not in json_data and os.environ.get("COMM_PASSWORD", "").strip():
        json_data["comm_password"] = os.environ["COMM_PASSWORD"]

    user = api.use(json_data.pop("broker"))
    user.prepare(**json_data)

    global_store["user"] = user
    return jsonify({"msg": "login success"}), 201


@app.route("/balance", methods=["GET"])
@error_handle
def get_balance():
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.balance), 200


@app.route("/position", methods=["GET"])
@error_handle
def get_position():
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.position), 200


@app.route("/auto_ipo", methods=["GET"])
@error_handle
def get_auto_ipo():
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.auto_ipo()), 200


@app.route("/today_entrusts", methods=["GET"])
@error_handle
def get_today_entrusts():
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.today_entrusts), 200


@app.route("/today_trades", methods=["GET"])
@error_handle
def get_today_trades():
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.today_trades), 200


@app.route("/cancel_entrusts", methods=["GET"])
@error_handle
def get_cancel_entrusts():
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.cancel_entrusts), 200


@app.route("/buy", methods=["POST"])
@error_handle
def post_buy():
    json_data = request.get_json(force=True)
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.buy(**json_data)), 201


@app.route("/sell", methods=["POST"])
@error_handle
def post_sell():
    json_data = request.get_json(force=True)
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.sell(**json_data)), 201


@app.route("/market_buy", methods=["POST"])
@error_handle
def post_market_buy():
    json_data = request.get_json(force=True)
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.market_buy(**json_data)), 201


@app.route("/market_sell", methods=["POST"])
@error_handle
def post_market_sell():
    json_data = request.get_json(force=True)
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.market_sell(**json_data)), 201


@app.route("/cancel_entrust", methods=["POST"])
@error_handle
def post_cancel_entrust():
    json_data = request.get_json(force=True)
    user, err = _get_user()
    if err:
        return err
    return jsonify(user.cancel_entrust(**json_data)), 201


@app.route("/exit", methods=["GET"])
@error_handle
def get_exit():
    user, err = _get_user()
    if err:
        return err
    user.exit()
    global_store.pop("user", None)
    return jsonify({"msg": "exit success"}), 200


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "接口不存在: {}".format(request.path)}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "方法不允许: {} {}".format(request.method, request.path)}), 405


def run(port=1430, api_key=None):
    global _api_key
    _api_key = api_key or os.environ.get("EASYTRADER_API_KEY", "")
    if not _api_key:
        logger.warning("API Key 未配置，Flask 服务无认证保护，请设置 EASYTRADER_API_KEY 环境变量")
    app.run(host="0.0.0.0", port=port)
