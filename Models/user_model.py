import re
from Models.database_config import ArangoDB
from datetime import datetime

db = ArangoDB()
# ------Bắt đầu tác vụ lấy thông tin từ Database------#

# Lấy thông tin Đại lý - Agency từ bảng Agent
def get_user():
    users = db.collection('Agent')
    #users = db.collection('dms_agent_detail')
    cursor = users.all()
    for user in cursor:
        return user  # Trả về user đầu tiên
    return None

# Build cây cho 1 area_code
def build_tree_for_area(agents):

    ### Xây dựng cây phân cấp cho 1 area_code.
    ### agents: list các dict chứa agent_code, agent_parent_code, area_code

    # Tạo map agent_code -> node (chỉ chứa agent_code, children)
    nodes_map = {
        a["agent_code"]: {
            "agent_code": a["agent_code"],
            "agent_name": a.get("agent_name", ""),
            "grade": a.get("grade", ""),
            "agent_status": a.get("agent_status", ""),
            "children": []
        }
        for a in agents
    }

    roots = []
    for agent in agents:
        parent_code = agent.get("agent_parent_code")

        # Nếu parent_code chứa ký tự không phải số => root trong area_code
        if parent_code and re.search(r"\D", parent_code):
            roots.append(nodes_map[agent["agent_code"]])
        else:
            # Nếu parent_code là số => tìm parent và gắn vào
            parent_node = nodes_map.get(parent_code)
            if parent_node:
                parent_node["children"].append(nodes_map[agent["agent_code"]])
            else:
                # Nếu không tìm thấy parent (lỗi dữ liệu) => cho vào root
                roots.append(nodes_map[agent["agent_code"]])
    return roots
# Build cây cho 1 Agent
def build_for_agent(agent):
    # Lấy dữ liệu
    users = db.aql.execute(f"""
    FOR a IN Agent 
        FILTER a.agent_code == "{agent}"
        RETURN a
    """)
    nodes = list(users)
    # Gom đại lý theo area_code
    area_groups = {}
    for n in nodes:
        su_code = n["area_code"]
        if su_code not in area_groups:
            area_groups[su_code] = []
        area_groups[su_code].append(n)

    # Build cây cho từng area_code
    tree = {}
    for ac, ag_list in area_groups.items():
        tree[ac] = build_tree_for_area(ag_list)

    # Root chứa toàn bộ area_code
    root = {
        "name": "ROOT",
        "children": [
            {
                "area_code": ac,
                "area_name": area_groups[ac][0].get("area_name", ""),
                "children": tree[ac]
            }
            for ac in tree
        ]
    }
    return root

# Build cây toàn bộ
def build_agent_tree(search_term=None):
    
    bind_vars = {}
    search_filter = ""

    if search_term:
        search_filter = """
            AND (
                LIKE(a.agent_code, @term, true) 
                OR LIKE(a.agent_name, @term, true)
            )
        """
        bind_vars["term"] = f"%{search_term}%"
        
    # Lấy dữ liệu
    # FOR a IN dms_agent_detail/Agent
    users = db.aql.execute("""
    FOR a IN Agent 
        """ + search_filter + """
        RETURN {
            area_code: a.area_code,
            area_name: a.area_name,       
            agent_code: a.agent_code,
            agent_name: a.agent_name,
            grade: a.grade,
            agent_status: a.agent_status,
            agent_parent_code: a.agent_parent_code
        }
    """, bind_vars=bind_vars)
    nodes = list(users)

    # Gom đại lý theo area_code
    area_groups = {}
    for n in nodes:
        su_code = n["area_code"]
        if su_code not in area_groups:
            area_groups[su_code] = []
        area_groups[su_code].append(n)

    # Build cây cho từng area_code
    tree = {}
    for ac, ag_list in area_groups.items():
        tree[ac] = build_tree_for_area(ag_list)

    # Root chứa toàn bộ area_code
    root = {
        "name": "ROOT",
        "children": [
            {
                "area_code": ac,
                "area_name": area_groups[ac][0].get("area_name", ""),
                "children": tree[ac]
            }
            for ac in tree
        ]
    }
    return root

# List detail calculate
def get_detail():
    query = """
    FOR doc IN Calculate_For_Detail
    FILTER LENGTH(
        FOR p IN doc.policies
        FILTER p.fyp > 0 OR p.fyc > 0
        RETURN 1
    ) > 0
    LIMIT 100
    RETURN doc
    """
    cursor = db.aql.execute(query)
    return list(cursor)
# List Commission Agent Calculated
def get_user_commission():
    users = db.collection('Calculate_For_Agent')
    cursor = users.find({'type_code': 'COM'})
    result = list(cursor)[:100]
    return result

# List Monthly Agent Calculated
def get_user_monthly():
    users = db.collection('Calculate_For_Agent')
    cursor = users.find({'type_code': 'MONTHLY'})
    result = list(cursor)[:100]
    return result

# Get _id Agent
def get_agent_id(agent_code):
    query = """
        FOR a IN Agent
            FILTER a.agent_code == @code
            LIMIT 1
            RETURN a._id
    """
    cursor = db.aql.execute(query, bind_vars={"code": agent_code})
    return next(cursor, None)  # trả về "Agent/<key>" hoặc None
    
# Get document Agent
def get_document_agent(agent_code):
    query = """
    FOR a IN Agent
        FILTER a.agent_code == @code
        RETURN a
    """
    bind_vars = {"code": agent_code}
    cursor = db.aql.execute(query, bind_vars=bind_vars)
    return next(cursor, None)

# Lấy tất cả các đại lý liên quan (downline) dành cho Transfer
def get_downline_transfer(agent_id):
    query = f"""
        FOR v, e, p IN 1..10 OUTBOUND "{agent_id}"
        GRAPH "Agent_Information"
        RETURN {{
            agent_code: v.agent_code,
            agent_name: v.agent_name,
            grade: v.grade,
            agent_status: v.agent_status
       }}
    """
    cursor = db.aql.execute(query)
    return list(cursor)

# Lấy tất cả các đại lý liên quan (downline) dành cho Terminate
def get_downline_terminate(agent_id):
    query = f"""
        FOR v, e, p IN 1..10 INBOUND "{agent_id}"
        GRAPH "Agent_Information"
        RETURN {{
            agent_code: v.agent_code,
            agent_name: v.agent_name,
            grade: v.grade,
            agent_status: v.agent_status
       }}
    """
    cursor = db.aql.execute(query)
    return list(cursor)

# Update status is Terminate
def Update_Status_Terminate(agent_code):
    query = """
        FOR a IN Agent
            FILTER a.agent_code == @agent_code
            UPDATE a WITH { agent_status: "Terminate" } IN Agent
            RETURN NEW
    """
    bind_vars = {"agent_code": agent_code}
    cursor = db.aql.execute(query, bind_vars=bind_vars)
    result = list(cursor)   
    return result

# Save movement hist
def Insert_Hist_Movement(agent_code , new_agent_code, movement_type: str):
    # 1) Lấy document hiện tại và leader mới
    current_agent = get_document_agent(agent_code)
    new_leader = get_document_agent(new_agent_code)
 
    print(f"----In data----")
    print(f"{current_agent}")
    print(f"{new_leader}")
    print(f"{movement_type}")
    if not current_agent or not new_leader:
        # Có thể raise hoặc trả về None/ thông điệp tùy bạn
        return None

    # 2) Tạo query với bind variables
    query = """
    INSERT {
        agent_code: @agent_code,
        old_reporting_to_code: @old_rt_code,
        new_reporting_to_code: @new_rt_code,
        movement_type: @movement_type,
        changed_at: @changed_at
    } INTO Agent_Movement_History
    RETURN NEW
    """

    bind_vars = {
        "agent_code": current_agent["agent_code"],
        "old_rt_code": current_agent.get("reporting_to_code", ""),
        "new_rt_code": new_leader["agent_code"],
        "movement_type": movement_type,
        "changed_at": datetime.now().isoformat()
    }

    # 3) Thực thi và trả kết quả
    cursor = db.aql.execute(query, bind_vars=bind_vars)
    return next(cursor, None)  # hoặc list(cursor) nếu muốn danh sách


