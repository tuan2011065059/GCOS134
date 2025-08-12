from arango import ArangoClient
import re

# Khởi tạo client & Truy cập Địa chỉ ArangoDB
client = ArangoClient(hosts="http://localhost:8529") 
# Kết nối tới server
db = client.db(
    #name="DMS",         # Tên database
    name="agency_db",                 
    username="root",            # Tên đăng nhập
    password="123456"       # Mật khẩu
)

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
    """
    Xây dựng cây phân cấp cho 1 area_code.
    agents: list các dict chứa agent_code, agent_parent_code, area_code
    """
    # Tạo map agent_code -> node (chỉ chứa agent_code, children)
    nodes_map = {
        a["agent_code"]: {
            "agent_code": a["agent_code"],
            "agent_name": a.get("agent_name", ""),
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
        
    # Lấy dữ liệu chỉ với agent_status = inforce
    # FOR a IN dms_agent_detail/Agent
    users = db.aql.execute("""
    FOR a IN dms_agent_detail 
        FILTER a.agent_status == "Inforce"
        """ + search_filter + """
        RETURN {
            area_code: a.area_code,
            area_name: a.area_name,       
            agent_code: a.agent_code,
            agent_name: a.agent_name,
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