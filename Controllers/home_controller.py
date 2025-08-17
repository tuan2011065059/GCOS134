from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, Response, url_for, redirect, flash
import json
import sys
import io
from Models.user_model import Insert_Hist_Movement, Update_Status_Terminate, get_document_agent ,build_agent_tree, get_user_commission, get_user_monthly, get_detail, get_agent_id, get_downline_transfer, get_downline_terminate
from Models.database_config import ArangoDB

home_blueprint = Blueprint('homepage', __name__)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
db = ArangoDB()
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

@home_blueprint.route("/agent-transfer")
def agent_transfer():
    return render_template("agent_transfer.html")

@home_blueprint.route("/agent-terminate")
def agent_terminate():
    return render_template("agent_terminate.html")
# List check terminate
@home_blueprint.route("/agent-terminate-tree", methods=["GET", "POST"])
def agent_terminate_tree():
    agent_code = ""
    message = None
    tree_data = []

    if request.method == "POST":
        action = request.form.get("action")
        agent_code = request.form.get("agent_code")

        if not agent_code:
            message = "❌ Vui lòng nhập Agent Code"
            return render_template("agent_terminate.html", message=message, tree=tree_data)

        if action == "search":
            searchID_agent = get_agent_id(agent_code)
            get_agent_code = get_document_agent(agent_code)
            agent_code = get_agent_code["agent_code"]
            if not get_agent_code:
                message = f"❌ Không tìm thấy đại lý {agent_code}"
            else:
                tree_data = get_downline_terminate(searchID_agent)
                agent_code = get_agent_code["agent_code"]
                if tree_data:
                    message = f"✅ Structure của đại lý {agent_code}"
                else:
                    message = f"⚠️ Đại lý {agent_code} không có downline"

        elif action == "terminate":
            searchID_agent = get_agent_id(agent_code)
            get_agent_code = get_document_agent(agent_code)
            agent_code = get_agent_code["agent_code"]
            if not searchID_agent:
                message = f"❌ Not invalid Agent {get_agent_code}"
            else:
                tree_data = get_downline_terminate(searchID_agent)
                if tree_data:
                    message = f"❌ Agent {agent_code} have Structure downline can't terminate"
                else:
                    result = Update_Status_Terminate(agent_code)
                    message = f"✅ Agent {agent_code} đã được terminate thành công"
                    # Lưu lịch sử
                    type = "Terminate"
                    update_hist = Insert_Hist_Movement(agent_code, agent_code, type)

    return render_template("agent_terminate.html", agent_code=agent_code, message=message, tree=tree_data)

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

# Chức năng transfer gợi ý
@home_blueprint.route('/suggest-reporting', methods=["GET", "POST"])
def suggest_reporting():
    result = []
    if request.method == "POST":
        agent_code = request.form.get("agent_code", "").strip()
        if agent_code:
            # Bước 1: Tìm vertex tương ứng với agent_code
            start_vertex = get_agent_id(agent_code)

            if start_vertex:
                # Bước 2: Lấy tất cả các đại lý liên quan (downline)
                result = get_downline_transfer(start_vertex)
            else:
                message = f"❌ Not invalid Agent {agent_code}"
                print(f"Không tìm thấy đại lý {agent_code}!")
    return render_template("agent_transfer.html", result=result, agent_code=agent_code, message=message)
    
# Cập nhật thông tin đại lý sau khi transfer
@home_blueprint.route("/do-transfer", methods=["POST"])
def do_transfer():
    current_agent_code = request.form.get("current_agent_code")
    new_leader_code = request.form.get("new_leader_code")

    if not current_agent_code or not new_leader_code:
        flash("❌ Thiếu dữ liệu để thực hiện transfer", "error")
        return redirect(url_for("homepage.suggest_reporting"))

    # 1. Lấy thông tin đại lý cần đổi
    current_agent = get_document_agent(current_agent_code)

    # 2. Lấy thông tin leader mới
    new_leader = get_document_agent(new_leader_code)

    if not current_agent or not new_leader:
        flash("❌ Không tìm thấy đại lý hoặc leader mới", "error")
        return redirect(url_for("homepage.suggest_reporting"))

    try:
        # 3. Cập nhật collection Agent
        update_query = f"""
            UPDATE "{current_agent['_key']}" WITH {{
                reporting_to_code: "{new_leader['agent_code']}",
                reporting_to_name: "{new_leader['agent_name']}",
                grade_reporting_to: "{new_leader.get('grade', '')}",
                agent_parent_code: "{new_leader['agent_code']}",
                grade_id_parent: "{new_leader.get('grade', '')}"
            }} IN Agent
        """
        db.aql.execute(update_query)

        # 4. Cập nhật Edge cho graph Agent_Information
        db.aql.execute(f"""
            FOR e IN Reporting_To
                FILTER e._from == "{current_agent['_id']}"
                REMOVE e IN Reporting_To
        """)
        db.aql.execute(f"""
            INSERT {{
                _from: "{current_agent['_id']}",
                _to: "{new_leader['_id']}"
            }} INTO Reporting_To
        """)

        # 5. Lưu lịch sử
        get_current_agent_code = current_agent['agent_code']
        get_current_new_leader_code = new_leader['agent_code']
        type = "Transfer"
        update_hist = Insert_Hist_Movement(get_current_agent_code, get_current_new_leader_code, type)
        flash(f"✅ Đã chuyển {current_agent['agent_code']} sang leader {new_leader['agent_code']}", "success")
    
    except Exception as e:
        flash(f"❌ Lỗi khi cập nhật: {str(e)}", "error")
    return redirect(url_for("homepage.suggest_reporting"))

# Lấy chi tiết thông tin đại lý
@home_blueprint.route('/api/agent-detail/<agent_code>', methods=['GET'])
def api_agent_detail(agent_code):
    # Nếu bạn chưa có hàm model, có thể làm trực tiếp ở đây:
    query = """
    FOR a IN Agent
      FILTER a.agent_code == @agent_code
      RETURN a
    """
    cursor = db.aql.execute(query, bind_vars={'agent_code': agent_code})
    detail = None
    for doc in cursor:
        detail = doc
        break

    if detail:
        return jsonify(detail)
    else:
        return jsonify({'error': 'Agent not found'}), 404