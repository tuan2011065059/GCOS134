from arango import ArangoClient

def ArangoDB():
	# Khởi tạo client & Truy cập Địa chỉ ArangoDB
	client = ArangoClient(hosts="http://localhost:8529") 
	# Kết nối tới server
	db = client.db(
   		#name="DMS",         # Tên database
    		name="DMS",                 
    		username="root",            # Tên đăng nhập
    		password="ntnqplnvtc"       # Mật khẩu
	)
	return db