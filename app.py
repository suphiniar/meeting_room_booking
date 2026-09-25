from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///room.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 用户模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="user") # user / admin

# 会议室模型
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

# 预约模型
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.String(50), nullable=False)
    end_time = db.Column(db.String(50), nullable=False)
    dept = db.Column(db.String(100))
    reason = db.Column(db.String(200))
    user = db.relationship('User', backref='bookings')
    room = db.relationship('Room', backref='bookings')

# 时间字符串转分钟 "08:30" -> 510
def time_to_minutes(time_str):
    try:
        hh, mm = map(int, time_str.split(":"))
        return hh * 60 + mm
    except:
        return None

# 初始化数据库，创建管理员账号
with app.app_context():
    db.create_all()
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        admin_user = User(username="admin", password=generate_password_hash("admin123"), role="admin")
        db.session.add(admin_user)
        db.session.commit()

# 登录
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash("登录成功")
            return redirect(url_for('index'))
        else:
            flash("账号或密码错误")
    return render_template('login.html')

# 注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_pwd = request.form['confirm_pwd']

        if username == "admin":
            flash("该用户名禁止注册！")
            return redirect(url_for('register'))
        if password != confirm_pwd:
            flash("两次输入密码不一致！")
            return redirect(url_for('register'))
        if len(password) < 6:
            flash("密码长度至少6位！")
            return redirect(url_for('register'))

        exist = User.query.filter_by(username=username).first()
        if exist:
            flash("用户名已存在！")
            return redirect(url_for('login'))
        
        new_user = User(username=username, password=generate_password_hash(password), role="user")
        db.session.add(new_user)
        db.session.commit()
        flash("注册成功，请登录！")
        return redirect(url_for('login'))
    return render_template('register.html')

# 主页
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    rooms = Room.query.all()
    bookings = Booking.query.join(Room).all()
    return render_template('index.html', rooms=rooms, bookings=bookings)

# 提交预约路由（增加：过去日期校验 + 最长4小时限制 + 冲突校验）
@app.route('/book', methods=['POST'])
def book():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    room_id = request.form['room_id']
    date_str = request.form['date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    dept = request.form['dept']
    reason = request.form['reason']

    # 1. 禁止预约过去日期
    today = str(date.today())
    if date_str < today:
        flash("不能预约过去的日期！")
        return redirect(url_for('index'))

    # 2. 时间格式校验
    start_min = time_to_minutes(start_time)
    end_min = time_to_minutes(end_time)
    if start_min is None or end_min is None:
        flash("时间格式错误，请使用 HH:mm，例如：08:30")
        return redirect(url_for('index'))
    if start_min >= end_min:
        flash("结束时间必须晚于开始时间！")
        return redirect(url_for('index'))

    # 3. 单次最长预约4小时
    duration = end_min - start_min
    max_duration = 4 * 60
    if duration > max_duration:
        flash("单次预约不能超过4小时！")
        return redirect(url_for('index'))

    # 4. 时间段冲突校验
    conflict_bookings = Booking.query.filter_by(room_id=room_id, date=date_str).all()
    for b in conflict_bookings:
        b_start = time_to_minutes(b.start_time)
        b_end = time_to_minutes(b.end_time)
        if start_min < b_end and end_min > b_start:
            flash(f"预约冲突！该会议室当日已有预约：{b.start_time} ~ {b.end_time}")
            return redirect(url_for('index'))

    # 创建预约
    new_booking = Booking(
        user_id=session['user_id'],
        room_id=room_id,
        date=date_str,
        start_time=start_time,
        end_time=end_time,
        dept=dept,
        reason=reason
    )
    db.session.add(new_booking)
    db.session.commit()
    flash("预约成功")
    return redirect(url_for('index'))

# 取消预约路由
@app.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel(booking_id):
    if 'user_id' not in session:
        flash("请先登录")
        return redirect(url_for('login'))
    booking = Booking.query.get_or_404(booking_id)
    if session['role'] != 'admin' and booking.user_id != session['user_id']:
        flash("无权取消该预约")
        return redirect(url_for('index'))
    db.session.delete(booking)
    db.session.commit()
    flash("预约已成功取消")
    return redirect(url_for('index'))

# 管理员页面
@app.route('/admin')
def admin_page():
    if 'user_id' not in session or session['role'] != 'admin':
        flash("无管理员权限")
        return redirect(url_for('index'))
    users = User.query.all()
    rooms = Room.query.all()
    bookings = Booking.query.join(Room).all()
    return render_template('admin.html', users=users, rooms=rooms, bookings=bookings)

# 添加会议室
@app.route('/add_room', methods=['POST'])
def add_room():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    name = request.form['room_name']
    new_room = Room(name=name)
    db.session.add(new_room)
    db.session.commit()
    flash("会议室添加成功")
    return redirect(url_for('admin'))

# 获取指定会议室+日期已占用时段（AJAX预览用）
@app.route('/get_occupied')
def get_occupied():
    room_id = request.args.get('room_id')
    date_str = request.args.get('date')
    occupied = Booking.query.filter_by(room_id=room_id, date=date_str).all()
    res = []
    for b in occupied:
        res.append({"start": b.start_time, "end": b.end_time})
    return {"occupied": res}

# 退出登录
@app.route('/logout')
def logout():
    session.clear()
    flash("已退出登录")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

