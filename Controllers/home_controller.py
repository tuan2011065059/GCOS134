from flask import Blueprint, render_template, jsonify, request, Response
import json
from Models.user_model import build_agent_tree, get_user_commission, get_user_monthly, get_detail
from arango import ArangoClient

home_blueprint = Blueprint('homepage', __name__)

# ------Bắt đầu tác vụ lấy/xử lý phương thức------#

# View Chính khi truy cập vào web
@home_blueprint.route('/')
def home():
    return render_template('base.html')

# View chi tiết thông tin đại lý
@home_blueprint.route('/agent-info')
def tree():
    tree_data = build_agent_tree()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Nếu request ajax: trả về JSON
        json_data = json.dumps(tree_data, ensure_ascii=False)
        return Response(json_data, mimetype='application/json')
    else:
        # Nếu request trình duyệt thường: trả về HTML
        return render_template('tree.html')

    return jsonify(tree_data)
# View chi tiết thông tin đại lý 2
@home_blueprint.route('/tree-view', methods=['GET'])
def treeview():
    search_term = request.args.get('searchInput', '').strip()

    if not search_term or search_term.lower() == "all":
        data = build_agent_tree()
    else:
        data = build_agent_tree(search_term)

    return Response(json.dumps(data, ensure_ascii=False), mimetype='application/json')


# View chi tiết lịch sử thay đổi chức vụ đại lý
@home_blueprint.route("/agent-movement")
def agent_movement():
    return render_template("agent_movement.html")

# View thực hiện appoint đại lý
@home_blueprint.route("/agent-appointment")
def agent_appointment():
    return render_template("agent_appointment.html")

# View Commission
@home_blueprint.route("/commission")
def commission():
    summary_data = get_user_commission()
    detail_data = get_detail()
    # Lấy tab đang active (mặc định summary)
    tab = request.args.get('tab', 'summary')
    # Lấy từ khóa tìm kiếm
    search = request.args.get('search', '').lower()
    if tab == 'summary':
        # Lọc dữ liệu summary theo search đơn giản theo agent_code hoặc agent_name
        filtered_data = [
            d for d in summary_data 
            if search in d['agent_code'].lower() or search in d['agent_name'].lower()
        ]
    else:
        # tab detail
        filtered_data = [
            d for d in detail_data 
            if search in d['agent_code'].lower() or search in d['agent_name'].lower()
        ]
    return render_template('commission.html', tab=tab, data=filtered_data, search=search)

# View Monthly
@home_blueprint.route("/monthly")
def monthly():
    summary_data = get_user_monthly()
    detail_data = get_detail()
    # Lấy tab đang active (mặc định summary)
    tab = request.args.get('tab', 'summary')
    # Lấy từ khóa tìm kiếm
    search = request.args.get('search', '').lower()
    if tab == 'summary':
        # Lọc dữ liệu summary theo search đơn giản theo agent_code hoặc agent_name
        filtered_data = [
            d for d in summary_data 
            if search in d['agent_code'].lower() or search in d['agent_name'].lower()
        ]
    else:
        # tab detail
        filtered_data = [
            d for d in detail_data 
            if search in d['agent_code'].lower() or search in d['agent_name'].lower()
        ]
    return render_template('monthly.html', tab=tab, data=filtered_data, search=search)

# Khởi tạo client & Truy cập Địa chỉ ArangoDB
client = ArangoClient(hosts="http://localhost:8529") 
# Kết nối tới server
db = client.db(
    name="agency_db",                 # Tên database
    #name="DMS",         # Tên database
    username="root",            # Tên đăng nhập
    password="123456"       # Mật khẩu
)
# View Movement - Phương thức get
@home_blueprint.route('/suggest-reporting', methods=['GET'])
def suggest_reporting():
    # Case null
    agent_code = request.args.get('agent_code')
    if not agent_code:
        return jsonify({"error": "agent_code is required"}), 400
    # Lấy agent hiện tại, case not found
    query_agent = """
    FOR a IN Agent
      FILTER a.agent_code == @agent_code
      RETURN a
    """
    cursor = db.aql.execute(query_agent, bind_vars={'agent_code': agent_code})
    agent = None
    for doc in cursor:
        agent = doc
        break
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    sales_unit_code = agent.get('sales_unit_code')
    if not sales_unit_code:
        return jsonify({"error": "sales_unit_code not found for agent"}), 400
    # Lấy danh sách agent cùng sales_unit_code, trừ agent hiện tại
    query_candidates = """
    FOR a IN Agent
      FILTER a.sales_unit_code == @sales_unit_code
        AND a.agent_code != @agent_code
      RETURN {
        agent_code: a.agent_code,
        agent_name: a.agent_name
      }
    """
    cursor = db.aql.execute(query_candidates, bind_vars={
        'sales_unit_code': sales_unit_code,
        'agent_code': agent_code
    })

    candidates = list(cursor)
    return jsonify({
        "agent_code": agent_code,
        "sales_unit_code": sales_unit_code,
        "candidates": candidates
    })

# View Movement - Phương thức post
@home_blueprint.route('/update-reporting', methods=['POST'])
def update_reporting():
    data = request.json
    agent_code = data.get('agent_code')
    new_reporting_code = data.get('new_reporting_code')  # agent_code mới

    if not agent_code or not new_reporting_code:
        return jsonify({"error": "agent_code and new_reporting_code are required"}), 400

    # Lấy document của agent cần update
    query_agent = """
    FOR a IN Agent
      FILTER a.agent_code == @agent_code
      RETURN a
    """
    cursor = db.aql.execute(query_agent, bind_vars={'agent_code': agent_code})
    agent = None
    for doc in cursor:
        agent = doc
        break

    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    # Cập nhật trường agent_parent_code (reporting_to)
    # Bạn có thể cập nhật thêm các trường liên quan nếu cần
    doc_key = agent['_key']
    update_data = {
        'agent_parent_code': new_reporting_code
    }
    updated = db.collection('Agent').update_match({'_key': doc_key}, update_data)

    if updated:
        return jsonify({"message": "Reporting updated successfully"})
    else:
        return jsonify({"error": "Failed to update reporting"}), 500
    
