from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, date
import os
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey123'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'room.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
# 用户表
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default="user")  # admin / user
    bookings = db.relationship('Booking', backref='creator', lazy=True)
# 会议室表
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    location = db.Column(db.String(120))
    capacity = db.Column(db.Integer)
    bookings = db.relationship('Booking', backref='room', lazy=True)
# 预约表
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    book_date = db.Column(db.String(30), nullable=False)
    start_time = db.Column(db.String(30), nullable=False)
    end_time = db.Column(db.String(30), nullable=False)
    booker_name = db.Column(db.String(80))
    department = db.Column(db.String(120))
    reason = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # 这条预约是谁创建的
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def is_time_overlap(s1, e1, s2, e2):
    fmt = "%H:%M"
    st1 = datetime.strptime(s1, fmt)
    et1 = datetime.strptime(e1, fmt)
    st2 = datetime.strptime(s2, fmt)
    et2 = datetime.strptime(e2, fmt)
    return st1 < et2 and et1 > st2
@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    selected_room_id = request.args.get("room_id")
    selected_date = request.args.get("date")
    rooms = Room.query.all()
    if not selected_room_id and rooms:
        selected_room_id = rooms[0].id
    if not selected_date:
        selected_date = date.today().isoformat()
    if request.method == "POST":
        room_id = request.form.get("room_id")
        book_date = request.form.get("book_date")
        start_t = request.form.get("start_time")
        end_t = request.form.get("end_time")
        booker_name_input = request.form.get("booker_name")
        department_input = request.form.get("department")
        reason_input = request.form.get("reason")
        # 管理员代预约：如果是管理员，可以选择创建人；普通用户创建人固定是自己
        create_uid = current_user.id
        if current_user.role == "admin" and request.form.get("create_user_id"):
            create_uid = request.form.get("create_user_id")
        today_str = date.today().isoformat()
        now_dt = datetime.now()
        select_day = datetime.strptime(book_date, "%Y-%m-%d").date()
        select_start_dt = datetime.strptime(f"{book_date} {start_t}", "%Y-%m-%d %H:%M")
        if select_day < now_dt.date():
            flash("不能预约过去的日期！")
            return redirect(url_for('index', room_id=room_id, date=book_date))
        if select_day == now_dt.date() and select_start_dt < now_dt:
            flash("不能预约当前时间之前的时段！")
            return redirect(url_for('index', room_id=room_id, date=book_date))
        if start_t >= end_t:
            flash("结束时间必须晚于开始时间！")
            return redirect(url_for('index', room_id=room_id, date=book_date))
        all_room_book = Booking.query.filter_by(room_id=room_id, book_date=book_date).all()
        conflict = False
        for b in all_room_book:
            if is_time_overlap(start_t, end_t, b.start_time, b.end_time):
                conflict = True
                break
        if conflict:
            flash("所选时间段和已有预约冲突！")
            return redirect(url_for('index', room_id=room_id, date=book_date))
        new_booking = Booking(
            room_id=room_id,
            book_date=book_date,
            start_time=start_t,
            end_time=end_t,
            booker_name=booker_name_input,
            department=department_input,
            reason=reason_input,
            user_id=create_uid
        )
        db.session.add(new_booking)
        db.session.commit()
        flash("预约提交成功！")
        return redirect(url_for('index', room_id=room_id, date=book_date))
    day_bookings = []
    if selected_room_id and selected_date:
        day_bookings = Booking.query.filter_by(room_id=selected_room_id, book_date=selected_date).order_by(Booking.start_time).all()
    all_users = User.query.all() if current_user.role == "admin" else []
    return render_template("index.html",
                           rooms=rooms,
                           selected_room_id=selected_room_id,
                           selected_date=selected_date,
                           day_bookings=day_bookings,
                           all_users=all_users)
# 删除预约
@app.route('/del_booking/<int:bid>', methods=['POST'])
@login_required
def del_booking(bid):
    if current_user.role != "admin":
        flash("无管理员权限")
        return redirect(url_for('index'))
    bk = Booking.query.get_or_404(bid)
    db.session.delete(bk)
    db.session.commit()
    flash("预约已删除")
    return redirect(url_for('index'))
# ---------------------- 管理员：会议室管理 ----------------------
@app.route('/admin_room', methods=['GET','POST'])
@login_required
def admin_room():
    if current_user.role != "admin":
        flash("只有管理员可以进入会议室管理页")
        return redirect(url_for('index'))
    if request.method == "POST":
        name = request.form.get("room_name")
        loc = request.form.get("location")
        cap = request.form.get("capacity")
        new_r = Room(name=name, location=loc, capacity=int(cap))
        db.session.add(new_r)
        db.session.commit()
        flash("会议室新增成功")
        return redirect(url_for("admin_room"))
    all_rooms = Room.query.all()
    return render_template("admin_room.html", all_rooms=all_rooms)
@app.route('/del_room/<int:rid>', methods=['POST'])
@login_required
def del_room(rid):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('index'))
    r = Room.query.get_or_404(rid)
    db.session.delete(r)
    db.session.commit()
    flash("会议室已删除")
    return redirect(url_for("admin_room"))
# ---------------------- 管理员：全部预约（支持搜索筛选） ----------------------
@app.route('/admin_all_booking')
@login_required
def admin_all_booking():
    if current_user.role != "admin":
        flash("只有管理员可以查看全部预约")
        return redirect(url_for('index'))
    room_id = request.args.get("f_room")
    s_date = request.args.get("f_date")
    s_name = request.args.get("f_booker")
    q = Booking.query.join(User).join(Room)
    if room_id:
        q = q.filter(Booking.room_id == room_id)
    if s_date:
        q = q.filter(Booking.book_date == s_date)
    if s_name:
        q = q.filter(Booking.booker_name.like(f"%{s_name}%"))
    all_booking = q.order_by(Booking.book_date, Booking.start_time).all()
    rooms = Room.query.all()
    return render_template("admin_all_booking.html", all_booking=all_booking, rooms=rooms)
# ---------------------- 管理员：用户管理（升级/降级管理员、删除用户、重置密码） ----------------------
@app.route('/admin_user', methods=['GET','POST'])
@login_required
def admin_user():
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template("admin_user.html", users=users)
@app.route('/admin_user_setrole/<int:uid>/<role>', methods=['POST'])
@login_required
def admin_user_setrole(uid, role):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('admin_user'))
    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        flash("不能修改自己的权限！")
        return redirect(url_for('admin_user'))
    if role not in ["admin", "user"]:
        flash("参数错误")
        return redirect(url_for('admin_user'))
    user.role = role
    db.session.commit()
    flash(f"已将用户【{user.username}】设置为 {role}")
    return redirect(url_for('admin_user'))
@app.route('/admin_user_del/<int:uid>', methods=['POST'])
@login_required
def admin_user_del(uid):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('admin_user'))
    user = User.query.get_or_404(uid)
    if user.id == current_user.id:
        flash("不能删除自己账号！")
        return redirect(url_for('admin_user'))
    db.session.delete(user)
    db.session.commit()
    flash("用户已删除")
    return redirect(url_for('admin_user'))
# 重置密码为 123456：管理员可以改自己、普通用户，不能改其他管理员
@app.route('/admin_reset_pwd/<int:uid>', methods=['POST'])
@login_required
def admin_reset_pwd(uid):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('admin_user'))
    user = User.query.get_or_404(uid)
    # 禁止修改其他管理员，允许自己和普通用户
    if user.role == "admin" and user.id != current_user.id:
        flash("不允许修改其他管理员的密码！")
        return redirect(url_for('admin_user'))
    user.password = "123456"
    db.session.commit()
    flash(f"用户【{user.username}】密码已重置为：123456，请通知用户修改")
    return redirect(url_for('admin_user'))

# 新增：自定义修改密码路由
@app.route('/admin_change_pwd/<int:uid>', methods=['POST'])
@login_required
def admin_change_pwd(uid):
    if current_user.role != "admin":
        flash("权限不足！")
        return redirect(url_for('admin_user'))
    user = User.query.get_or_404(uid)
    if user.role == "admin" and user.id != current_user.id:
        flash("不允许修改其他管理员的密码！")
        return redirect(url_for('admin_user'))
    new_pwd = request.form.get("new_pwd")
    if not new_pwd:
        flash("密码不能为空！")
        return redirect(url_for('admin_user'))
    user.password = new_pwd
    db.session.commit()
    flash(f"用户【{user.username}】密码修改成功")
    return redirect(url_for('admin_user'))

# ---------------------- 管理员：数据统计看板 ----------------------
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('index'))
    today = date.today().isoformat()
    today_count = Booking.query.filter_by(book_date=today).count()
    total_booking = Booking.query.count()
    total_user = User.query.count()
    total_room = Room.query.count()
    # 每个会议室预约次数统计
    room_stat = db.session.query(Room.name, db.func.count(Booking.id)).outerjoin(Booking).group_by(Room.id).all()
    return render_template("admin_dashboard.html",
                           today_count=today_count,
                           total_booking=total_booking,
                           total_user=total_user,
                           total_room=total_room,
                           room_stat=room_stat)
# 登录注册登出
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("账号或密码错误")
    return render_template("login.html")
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash("用户名已经被占用，请换一个")
            return redirect(url_for('register'))
        new_user = User(username=username, password=password, role="user")
        db.session.add(new_user)
        db.session.commit()
        flash("注册成功！请返回登录")
        return redirect(url_for('login'))
    return render_template("register.html")
if __name__ == '__main__':
    app.run(debug=True)
