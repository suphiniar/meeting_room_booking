from flask import Flask, request, jsonify, render_template_string, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "meeting_room_2026_secret_abc"
DB_FILE = "meeting_server.db"

USER_LIST = {
    "admin": {"pwd": "admin123", "role": "admin"},
    "user1": {"pwd": "123456", "role": "user"},
    "user2": {"pwd": "123456", "role": "user"}
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS rooms
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS orders
                   (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER,
                    room_name TEXT,
                    date TEXT,
                    start TEXT,
                    end TEXT,
                    userName TEXT,
                    dept TEXT,
                    reason TEXT,
                    FOREIGN KEY(room_id) REFERENCES rooms(id))''')
    cur.execute("SELECT COUNT(*) FROM rooms")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO rooms(name) VALUES (?)",
                        [("401",), ("405",), ("409",)])
    conn.commit()
    conn.close()

HTML_PAGE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>会议室预约系统</title>
    <style>
        * {
            box-sizing: border-box;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 0;
        }
        body {
            background-color: #f4f7fa;
            padding: 20px 12px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        h2 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 20px;
            font-size:22px;
        }
        h4{
            margin-bottom:10px;
            color:#2c3e50;
            font-size:17px;
        }
        .card {
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            padding: 18px;
            margin-bottom: 16px;
        }
        .form-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom:14px;
        }
        label {
            font-weight: 500;
            color:#34495e;
            font-size:14px;
        }
        input, select {
            padding:8px 10px;
            border:1px solid #dcdfe6;
            border-radius:6px;
            font-size:14px;
        }
        button {
            padding:8px 14px;
            border: none;
            border-radius:6px;
            cursor:pointer;
            font-size:14px;
            transition: 0.2s;
        }
        .btn-primary {
            background-color: #409eff;
            color:#fff;
        }
        .btn-primary:hover {
            background-color:#66b1ff;
        }
        .btn-danger {
            background-color:#f56c6c;
            color:#fff;
        }
        .btn-danger:hover {
            background-color:#f78989;
        }
        .btn-default {
            background-color:#909399;
            color:#fff;
        }
        .btn-default:hover {
            background-color:#a6a9ad;
        }
        .btn-success{
            background-color:#67c23a;
            color:#fff;
        }
        .btn-success:hover{
            background-color:#85d15c;
        }
        .time-grid {
            display:grid;
            grid-template-columns: repeat(5,1fr);
            gap:8px;
            margin-top:12px;
        }
        .slot {
            padding:14px 4px;
            text-align:center;
            border-radius:8px;
            font-weight:500;
            font-size:14px;
        }
        .free {
            background-color:#e1f3d8;
            color:#2f541d;
        }
        .used {
            background-color:#fde2e2;
            color:#8c2020;
            cursor:not-allowed;
        }
        table {
            width:100%;
            border-collapse: collapse;
            margin-top:10px;
        }
        th,td {
            padding:8px 6px;
            border-bottom:1px solid #ebeef5;
            text-align:center;
            font-size:13px;
        }
        th {
            background-color:#f5f7fa;
            color:#606266;
        }
        .login-card{
            max-width:420px;
            margin:80px auto;
        }
        .tip{
            color:#909399;
            font-size:12px;
            margin-bottom:8px;
        }
    </style>
</head>
<body>
<div class="container" id="app">
    <div id="loginArea">
        <div class="card login-card">
            <h2>登录会议室预约系统</h2>
            <div class="form-row">
                <label>账号</label>
                <input id="username" placeholder="输入账号">
            </div>
            <div class="form-row">
                <label>密码</label>
                <input id="password" type="password" placeholder="输入密码">
            </div>
            <div class="tip">管理员 admin/admin123；普通用户 user1/123456 user2/123456</div>
            <button class="btn-primary" onclick="login()">登录</button>
        </div>
    </div>

    <div id="mainArea" style="display:none;">
        <h2>会议室预约系统</h2>

        <div class="card" id="roomManageCard" style="display:none;">
            <h4>会议室管理（管理员）</h4>
            <div class="form-row">
                <input id="newRoomName" placeholder="新增会议室名称，例如：410">
                <button class="btn-success" onclick="addRoom()">新增会议室</button>
            </div>
            <div class="form-row">
                <select id="editRoomSelect"></select>
                <input id="editRoomName" placeholder="修改名称">
                <button class="btn-primary" onclick="updateRoom()">修改</button>
                <button class="btn-danger" onclick="deleteRoom()">删除会议室</button>
            </div>
            <div class="tip">删除会议室：该会议室不能存在任何预约记录</div>
        </div>

        <div class="card">
            <div class="form-row">
                <label>会议室：</label>
                <select id="roomSelect"></select>
                <label>日期：</label>
                <input type="date" id="dateInput">
                <button class="btn-primary" onclick="renderTimeTable()">刷新时段</button>
            </div>
            <div class="tip">🟢 空闲可预约　🔴 已占用</div>
            <div class="time-grid" id="timeGrid"></div>
        </div>

        <div class="card">
            <h4>预约信息</h4>
            <div class="form-row">
                <label>选中时段：</label>
                <input id="startTime" placeholder="开始时间" readonly style="width:90px;">
                <span>~</span>
                <input id="endTime" placeholder="结束时间" readonly style="width:90px;">
            </div>
            <div class="form-row">
                <label>预约人：</label>
                <input id="userName" placeholder="姓名">
                <label>部门：</label>
                <input id="dept" placeholder="部门">
                <label>事由：</label>
                <input id="reason" placeholder="会议事由">
            </div>
            <div class="form-row">
                <button class="btn-primary" onclick="submitOrder()">提交预约</button>
                <button class="btn-primary" onclick="openAllOrders()">查看全部预约记录</button>
                <button class="btn-default" onclick="logout()">退出登录</button>
            </div>
        </div>

        <div class="card" id="orderPanel" style="display:none;">
            <h4>全部预约记录</h4>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>会议室</th>
                        <th>日期</th>
                        <th>开始</th>
                        <th>结束</th>
                        <th>预约人</th>
                        <th>部门</th>
                        <th>事由</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody id="orderTableBody"></tbody>
            </table>
            <button class="btn-default" onclick="closeOrderPanel()" style="margin-top:12px;">关闭</button>
        </div>
    </div>
</div>

<script>
let userRole = "";
let roomList = [];
document.getElementById('dateInput').valueAsDate = new Date();

async function loadRooms(){
    const res = await fetch('/api/rooms');
    roomList = await res.json();
    const roomSelect = document.getElementById("roomSelect");
    const editRoomSelect = document.getElementById("editRoomSelect");
    roomSelect.innerHTML = "";
    editRoomSelect.innerHTML = "";
    roomList.forEach(r=>{
        roomSelect.innerHTML += `<option value="${r.id}">${r.name}</option>`;
        editRoomSelect.innerHTML += `<option value="${r.id}">${r.name}</option>`;
    })
    renderTimeTable();
}

async function addRoom(){
    const name = document.getElementById("newRoomName").value.trim();
    if(!name){alert("请输入会议室名称");return;}
    const res = await fetch("/api/rooms",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({name})
    });
    const ret = await res.json();
    if(ret.ok){
        alert("新增成功");
        document.getElementById("newRoomName").value="";
        loadRooms();
    }else{
        alert(ret.msg);
    }
}
async function updateRoom(){
    const rid = document.getElementById("editRoomSelect").value;
    const newName = document.getElementById("editRoomName").value.trim();
    if(!newName){alert("请输入新名称");return;}
    const res = await fetch(`/api/rooms/${rid}`,{
        method:"PUT",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({name:newName})
    });
    const ret = await res.json();
    if(ret.ok){
        alert("修改成功");
        document.getElementById("editRoomName").value="";
        loadRooms();
    }else{
        alert(ret.msg);
    }
}
async function deleteRoom(){
    const rid = document.getElementById("editRoomSelect").value;
    if(!confirm("确定删除该会议室？如果里面存在预约，则无法删除！")) return;
    const res = await fetch(`/api/rooms/${rid}`,{method:"DELETE"});
    const ret = await res.json();
    if(ret.ok){
        alert("删除成功");
        loadRooms();
    }else{
        alert(ret.msg);
    }
}

async function login(){
    const username = document.getElementById("username").value.trim();
    const pwd = document.getElementById("password").value.trim();
    const res = await fetch("/api/login",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({username,pwd})
    });
    const ret = await res.json();
    if(ret.ok){
        userRole = ret.role;
        document.getElementById("loginArea").style.display="none";
        document.getElementById("mainArea").style.display="block";
        if(userRole === "admin"){
            document.getElementById("roomManageCard").style.display="block";
        }
        await loadRooms();
    }else{
        alert(ret.msg);
    }
}

async function logout(){
    await fetch("/api/logout");
    document.getElementById("loginArea").style.display="block";
    document.getElementById("mainArea").style.display="none";
    document.getElementById("roomManageCard").style.display="none";
    userRole = "";
}

async function renderTimeTable(){
    const roomId = document.getElementById("roomSelect").value;
    const date = document.getElementById("dateInput").value;
    const res = await fetch('/api/orders?roomId='+roomId+'&date='+date);
    const usedList = await res.json();
    const grid = document.getElementById("timeGrid");
    grid.innerHTML = "";
    for(let h=8;h<18;h++){
        const s = `${h.toString().padStart(2,'0')}:00`;
        const e = `${(h+1).toString().padStart(2,'0')}:00`;
        const isUsed = usedList.some(ord=>!(ord.end <= s || ord.start >= e));
        const div = document.createElement("div");
        div.className = "slot " + (isUsed ? "used" : "free");
        div.innerText = `${s}-${e}`;
        if(!isUsed){
            div.onclick = ()=>{
                document.getElementById("startTime").value = s;
                document.getElementById("endTime").value = e;
            }
        }
        grid.appendChild(div);
    }
}

async function submitOrder(){
    const roomId = document.getElementById("roomSelect").value;
    const roomObj = roomList.find(r=>r.id == roomId);
    const roomName = roomObj.name;
    const date = document.getElementById("dateInput").value;
    const start = document.getElementById("startTime").value;
    const end = document.getElementById("endTime").value;
    const userName = document.getElementById("userName").value.trim();
    const dept = document.getElementById("dept").value.trim();
    const reason = document.getElementById("reason").value.trim();
    if(!start || !end || !userName || !dept || !reason){
        alert("请填写完整预约信息并选择空闲时段！");
        return;
    }
    const payload = {roomId, roomName, date, start, end, userName, dept, reason};
    const res = await fetch('/api/orders',{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify(payload)
    });
    const ret = await res.json();
    if(ret.ok){
        alert("预约成功！");
        renderTimeTable();
        document.getElementById("startTime").value = "";
        document.getElementById("endTime").value = "";
        document.getElementById("userName").value = "";
        document.getElementById("dept").value = "";
        document.getElementById("reason").value = "";
    }else{
        alert(ret.msg);
    }
}

async function openAllOrders(){
    const res = await fetch('/api/all_orders');
    const orders = await res.json();
    const tbody = document.getElementById("orderTableBody");
    tbody.innerHTML = "";
    orders.forEach(item=>{
        const tr = document.createElement("tr");
        let delBtn = "";
        if(userRole === "admin"){
            delBtn = `<button class="btn-danger" onclick="deleteOrder(${item.id})">删除</button>`;
        }
        tr.innerHTML = `
            <td>${item.id}</td>
            <td>${item.roomName}</td>
            <td>${item.date}</td>
            <td>${item.start}</td>
            <td>${item.end}</td>
            <td>${item.userName}</td>
            <td>${item.dept}</td>
            <td>${item.reason}</td>
            <td>${delBtn}</td>
        `;
        tbody.appendChild(tr);
    })
    document.getElementById("orderPanel").style.display = "block";
}

async function deleteOrder(id){
    if(!confirm("确定删除这条预约记录？")) return;
    const res = await fetch('/api/order/'+id, {method:"DELETE"});
    const ret = await res.json();
    if(ret.ok){
        alert("删除成功");
        openAllOrders();
        renderTimeTable();
    }else{
        alert(ret.msg);
    }
}

function closeOrderPanel(){
    document.getElementById("orderPanel").style.display = "none";
}

document.getElementById("roomSelect").onchange = renderTimeTable;
document.getElementById("dateInput").onchange = renderTimeTable;
</script>
</body>
'''

@app.route('/')
def index():
    init_db()
    return render_template_string(HTML_PAGE)

@app.route('/api/rooms')
def get_rooms():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT id,name FROM rooms").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/rooms', methods=["POST"])
def add_room():
    if session.get("role") != "admin":
        return jsonify({"ok":False,"msg":"无权限"})
    data = request.get_json()
    name = data.get("name","").strip()
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO rooms(name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        return jsonify({"ok":True})
    except sqlite3.IntegrityError:
        return jsonify({"ok":False,"msg":"会议室名称已存在！"})

@app.route('/api/rooms/<int:rid>', methods=["PUT"])
def edit_room(rid):
    if session.get("role") != "admin":
        return jsonify({"ok":False,"msg":"无权限"})
    data = request.get_json()
    newName = data.get("name","").strip()
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE rooms SET name=? WHERE id=?", (newName, rid))
        cur.execute("UPDATE orders SET room_name=? WHERE room_id=?", (newName, rid))
        conn.commit()
        conn.close()
        return jsonify({"ok":True})
    except sqlite3.IntegrityError:
        return jsonify({"ok":False,"msg":"名称重复！"})

@app.route('/api/rooms/<int:rid>', methods=["DELETE"])
def del_room(rid):
    if session.get("role") != "admin":
        return jsonify({"ok":False,"msg":"无权限"})
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cnt = cur.execute("SELECT COUNT(*) FROM orders WHERE room_id=?", (rid,)).fetchone()[0]
    if cnt>0:
        conn.close()
        return jsonify({"ok":False,"msg":"该会议室存在预约记录，不能删除！"})
    cur.execute("DELETE FROM rooms WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/login', methods=["POST"])
def login_api():
    data = request.get_json()
    username = data.get("username","")
    pwd = data.get("pwd","")
    if username in USER_LIST and USER_LIST[username]["pwd"] == pwd:
        session["user"] = username
        session["role"] = USER_LIST[username]["role"]
        return jsonify({"ok":True, "role": session["role"]})
    return jsonify({"ok":False,"msg":"账号密码错误"})

@app.route('/api/logout')
def logout_api():
    session.clear()
    return jsonify({"ok":True})

@app.route('/api/orders')
def get_orders():
    roomId = request.args.get("roomId")
    date = request.args.get("date")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM orders WHERE room_id=? AND date=?", (roomId, date)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/all_orders')
def get_all_orders():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM orders ORDER BY date, start").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/orders', methods=["POST"])
def add_order():
    data = request.get_json()
    roomId = data["roomId"]
    date = data["date"]
    start = data["start"]
    end = data["end"]
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    conflict = cur.execute('''SELECT id FROM orders WHERE room_id=? AND date=?
                           AND NOT(end <= ? OR start >= ?)''', (roomId, date, start, end)).fetchone()
    if conflict:
        conn.close()
        return jsonify({"ok":False, "msg":"该时段已经被预约！"})
    cur.execute('''INSERT INTO orders(room_id,room_name,date,start,end,userName,dept,reason)
                VALUES (?,?,?,?,?,?,?,?)''',
                (data["roomId"],data["roomName"],data["date"],data["start"],data["end"],
                 data["userName"],data["dept"],data["reason"]))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/order/<int:oid>', methods=["DELETE"])
def del_order(oid):
    if session.get("role") != "admin":
        return jsonify({"ok":False,"msg":"无权限"})
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("DELETE FROM orders WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

if __name__ == '__main__':
    app.run()
