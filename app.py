from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
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
    role = db.Column(db.String(20), default="user")  # user / manager / admin
    department = db.Column(db.String(64))
    office = db.Column(db.String(64))
    staff_id = db.Column(db.String(32))
    bookings = db.relationship('Booking', backref='creator', lazy=True)
# 会议室
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    location = db.Column(db.String(120))
    capacity = db.Column(db.Integer)
    bookings = db.relationship('Booking', backref='room', lazy=True)
# 预约记录
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    book_date = db.Column(db.String(30), nullable=False)
    start_time = db.Column(db.String(20), nullable=False)
    end_time = db.Column(db.String(20), nullable=False)
    booker_name = db.Column(db.String(80))
    department = db.Column(db.String(80))
    reason = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
# 共享路径主表
class SharePath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dept = db.Column(db.String(64))
    office = db.Column(db.String(64))
    name = db.Column(db.String(32))
    staff_id = db.Column(db.String(32))
    share_url = db.Column(db.String(256))
    remark = db.Column(db.String(256))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now)
    owner = db.relationship('User', backref='share_paths')
# 共享申请表【修改：target_path_id 允许为 NULL】
class ShareApply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_path_id = db.Column(db.Integer, db.ForeignKey('share_path.id'), nullable=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.String(256))
    status = db.Column(db.String(16), default="pending")  # pending / pass / reject
    create_time = db.Column(db.DateTime, default=datetime.now)
    target_path = db.relationship('SharePath', backref='view_applies')
    applicant = db.relationship('User', backref='apply_records')
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def is_time_overlap(s1, e1, s2, e2):
    return not (e1 <= s2 or e2 <= s1)
# 登录注册注销
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = User.query.filter_by(username=request.form['username']).first()
        if u and check_password_hash(u.password, request.form['password']):
            login_user(u)
            return redirect(url_for('module_index'))
        flash("账号密码错误")
    return render_template("login.html")
@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password']
        department = None
        office = None
        staff_id = None
        if User.query.filter_by(username=username).first():
            flash("用户名已存在")
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            password=hashed_pw,
            role="user",
            department=department,
            office=office,
            staff_id=staff_id
        )
        db.session.add(new_user)
        db.session.commit()
        flash("注册成功，请登录")
        return redirect(url_for('login'))
    return render_template("register.html")
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
@app.route('/module')
@login_required
def module_index():
    return render_template("module_index.html")
# 会议室预约
@app.route('/', methods=["GET", "POST"])
@login_required
def index():
    selected_room_id = request.args.get("room_id")
    selected_date = request.args.get("date", date.today().isoformat())
    today_iso = date.today().isoformat()
    rooms = Room.query.all()
    if not selected_room_id and rooms:
        selected_room_id = rooms[0].id
    day_bookings = Booking.query.filter_by(room_id=selected_room_id, book_date=selected_date).all()
    all_users = []
    if current_user.role in ["admin", "manager"]:
        all_users = User.query.all()
    if request.method == "POST":
        rid = request.form.get("room_id")
        bdate = request.form.get("book_date")
        st = request.form.get("start_time")
        et = request.form.get("end_time")
        bname = request.form.get("booker_name")
        dept = request.form.get("department")
        reason = request.form.get("reason")
        create_uid = request.form.get("create_user_id", current_user.id)
        if bdate < today_iso:
            flash("不能预约过去日期")
            return redirect(url_for('index', room_id=rid, date=bdate))
        conflict = False
        for b in Booking.query.filter_by(room_id=rid, book_date=bdate).all():
            if is_time_overlap(st, et, b.start_time, b.end_time):
                conflict = True
                break
        if conflict:
            flash("该时段已有预约，冲突！")
            return redirect(url_for('index', room_id=rid, date=bdate))
        new_booking = Booking(
            room_id=rid,
            book_date=bdate,
            start_time=st,
            end_time=et,
            booker_name=bname,
            department=dept,
            reason=reason,
            user_id=create_uid
        )
        db.session.add(new_booking)
        db.session.commit()
        flash("预约成功")
        return redirect(url_for('index', room_id=rid, date=bdate))
    return render_template("index.html",
                           rooms=rooms,
                           selected_room_id=selected_room_id,
                           selected_date=selected_date,
                           today=today_iso,
                           day_bookings=day_bookings,
                           all_users=all_users)
@app.route('/del_booking/<int:bid>', methods=["POST"])
@login_required
def del_booking(bid):
    bk = Booking.query.get_or_404(bid)
    creator = bk.creator
    allow = False
    if current_user.role == "admin":
        allow = True
    elif current_user.role == "manager":
        if bk.user_id == current_user.id or creator.role == "user":
            allow = True
    else:
        if bk.user_id == current_user.id:
            allow = True
    if not allow:
        flash("无权删除")
        return redirect(url_for('index'))
    db.session.delete(bk)
    db.session.commit()
    flash("已取消预约")
    return redirect(url_for('index'))

# ========== 修改后的 admin_room 路由 + 新增 del_room ==========
@app.route('/admin_room', methods=["GET", "POST"])
@login_required
def admin_room():
    if current_user.role != "admin":
        flash("只有admin管理员可以管理会议室")
        return redirect(url_for('index'))

    if request.method == "POST":
        rn = request.form.get("room_name").strip()
        loc = request.form.get("location").strip()
        cap = request.form.get("capacity")
        # 查重：同名会议室禁止新增
        exist_room = Room.query.filter_by(name=rn).first()
        if exist_room:
            flash("该会议室名称已存在，不允许重复添加！")
            return redirect(url_for("admin_room"))
        new_r = Room(name=rn, location=loc, capacity=cap)
        db.session.add(new_r)
        db.session.commit()
        flash("会议室添加成功")

    rooms = Room.query.all()
    return render_template("admin_room.html", rooms=rooms)

@app.route('/del_room/<int:rid>', methods=["POST"])
@login_required
def del_room(rid):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('index'))
    room = Room.query.get_or_404(rid)
    db.session.delete(room)
    db.session.commit()
    flash("会议室已删除")
    return redirect(url_for("admin_room"))
# =========================================================

@app.route('/admin_all_booking')
@login_required
def admin_all_booking():
    if current_user.role not in ["admin", "manager"]:
        flash("权限不足")
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
    all_b = q.order_by(Booking.book_date, Booking.start_time).all()
    rooms = Room.query.all()
    return render_template("admin_all_booking.html", all_booking=all_b, rooms=rooms)
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role not in ["admin", "manager"]:
        flash("权限不足")
        return redirect(url_for('index'))
    today_iso = date.today().isoformat()
    today_cnt = Booking.query.filter_by(book_date=today_iso).count()
    total_booking = Booking.query.count()
    total_user = User.query.count()
    total_room = Room.query.count()
    room_stats = db.session.query(Room.name, db.func.count(Booking.id)).outerjoin(Booking).group_by(Room.id, Room.name).all()
    return render_template("admin_dashboard.html",
                           today_count=today_cnt,
                           total_booking=total_booking,
                           total_user=total_user,
                           total_room=total_room,
                           room_stat=room_stats)
@app.route('/admin_user', methods=["GET", "POST"])
@login_required
def admin_user():
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template("admin_user.html", users=users)
@app.route('/admin_user_setrole/<int:uid>/<role>', methods=["POST"])
@login_required
def admin_user_setrole(uid, role):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('admin_user'))
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        flash("不能修改自己权限")
        return redirect(url_for('admin_user'))
    if role not in ["user", "manager", "admin"]:
        flash("非法角色")
        return redirect(url_for('admin_user'))
    u.role = role
    db.session.commit()
    flash("角色已更新")
    return redirect(url_for('admin_user'))
@app.route('/admin_user_del/<int:uid>', methods=["POST"])
@login_required
def admin_user_del(uid):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('admin_user'))
    u = User.query.get_or_404(uid)
    if u.id == current_user.id:
        flash("不能删除自己！")
        return redirect(url_for('admin_user'))
    db.session.delete(u)
    db.session.commit()
    flash("用户已删除")
    return redirect(url_for('admin_user'))
@app.route('/admin_change_pwd/<int:uid>', methods=["POST"])
@login_required
def admin_change_pwd(uid):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('admin_user'))
    u = User.query.get_or_404(uid)
    new_pwd = request.form.get("new_pwd")
    if not new_pwd:
        flash("密码不能为空")
        return redirect(url_for('admin_user'))
    u.password = generate_password_hash(new_pwd)
    db.session.commit()
    flash("密码修改成功")
    return redirect(url_for('admin_user'))
@app.route('/admin_reset_pwd/<int:uid>', methods=["POST"])
@login_required
def admin_reset_pwd(uid):
    if current_user.role != "admin":
        flash("权限不足")
        return redirect(url_for('admin_user'))
    u = User.query.get_or_404(uid)
    u.password = generate_password_hash("123456")
    db.session.commit()
    flash("密码已重置为123456")
    return redirect(url_for('admin_user'))
# ==================== 共享路径模块 ====================
@app.route('/share', methods=["GET", "POST"])
@login_required
def share_page():
    search_name = request.args.get("search_name", "").strip()
    search_staff = request.args.get("search_staff", "").strip()
    if request.method == "POST":
        dept_input = request.form.get("dept","").strip()
        office_input = request.form.get("office","").strip()
        name_input = request.form.get("name","").strip()
        staffid_input = request.form.get("staff_id","").strip()
        share_url = request.form.get("share_url","").strip()
        remark = request.form.get("remark","").strip()
        new_path = SharePath(
            dept=dept_input,
            office=office_input,
            name=name_input,
            staff_id=staffid_input,
            share_url=share_url,
            remark=remark,
            user_id=current_user.id
        )
        db.session.add(new_path)
        db.session.commit()
        flash("新增共享路径成功")
        return redirect(url_for("share_page"))
    query = SharePath.query
    if search_name:
        query = query.filter(SharePath.name.like(f"%{search_name}%"))
    if search_staff:
        query = query.filter(SharePath.staff_id.like(f"%{search_staff}%"))
    path_list = query.order_by(SharePath.create_time.desc()).all()
    passed_apply_ids = set()
    passed_apps = ShareApply.query.filter_by(applicant_id=current_user.id, status="pass").all()
    for ap in passed_apps:
        passed_apply_ids.add(ap.target_path_id)
    # 我收到的待审核申请（只pending）
    my_applies = ShareApply.query.join(SharePath).filter(
        SharePath.user_id == current_user.id,
        ShareApply.status == "pending"
    ).all()
    return render_template("share_path.html",
                           path_list=path_list,
                           search_name=search_name,
                           search_staff=search_staff,
                           my_applies=my_applies,
                           passed_apply_ids=passed_apply_ids)
# 删除共享路径【修复update语法】
@app.route('/share_del/<int:pid>', methods=["POST"])
@login_required
def share_del(pid):
    item = SharePath.query.get_or_404(pid)
    if not (item.user_id == current_user.id or current_user.role == "admin"):
        flash("无权删除该共享路径")
        return redirect(url_for("share_page"))
    # 遍历所有关联申请，置空外键
    applies = ShareApply.query.filter_by(target_path_id=pid).all()
    for ap in applies:
        ap.target_path_id = None
    db.session.delete(item)
    db.session.commit()
    flash("共享路径已删除，相关申请记录保留（原路径已解除关联）")
    return redirect(url_for("share_page"))


# 编辑共享路径：仅本人
@app.route('/share/edit/<int:pid>', methods=["GET", "POST"])
@login_required
def share_edit(pid):
    item = SharePath.query.get_or_404(pid)
    if item.user_id != current_user.id:
        flash("你没有权限编辑这条记录")
        return redirect(url_for('share_page'))
    if request.method == "POST":
        item.dept = request.form.get("dept","").strip()
        item.office = request.form.get("office","").strip()
        item.name = request.form.get("name","").strip()
        item.staff_id = request.form.get("staff_id","").strip()
        item.share_url = request.form.get("share_url","").strip()
        item.remark = request.form.get("remark","").strip()
        db.session.commit()
        flash("编辑保存成功")
        return redirect(url_for('share_page'))
    return render_template("share_edit.html", item=item)
# 发起查看申请
@app.route('/share_apply_view/<int:pid>', methods=["POST"])
@login_required
def share_apply_view(pid):
    target_path = SharePath.query.get_or_404(pid)
    if current_user.role == "admin":
        flash("管理员无需申请查看")
        return redirect(url_for('share_page'))
    if target_path.user_id == current_user.id:
        flash("无需申请查看自己的路径")
        return redirect(url_for('share_page'))
    exist = ShareApply.query.filter_by(target_path_id=pid, applicant_id=current_user.id, status="pending").first()
    if exist:
        flash("你已经提交过这条路径的查看申请，请等待处理")
        return redirect(url_for('share_page'))
    apply_item = ShareApply(
        target_path_id=pid,
        applicant_id=current_user.id,
        reason=request.form["apply_reason"]
    )
    db.session.add(apply_item)
    db.session.commit()
    flash("查看申请已提交，等待路径所属人审核")
    return redirect(url_for('share_page'))
# 所有者审核申请
@app.route('/share_review_view/<int:aid>/<action>', methods=["POST"])
@login_required
def share_review_view(aid, action):
    apply_item = ShareApply.query.get_or_404(aid)
    # 注意：如果原路径已经被删掉，apply_item.target_path 是 None
    if not apply_item.target_path or apply_item.target_path.user_id != current_user.id:
        flash("只有该共享路径的所有者可以审核")
        return redirect(url_for('share_page'))
    if apply_item.status != "pending":
        flash("申请已经审核完毕，不可重复操作")
        return redirect(url_for('share_page'))
    if action == "pass":
        apply_item.status = "pass"
        flash("已同意对方查看")
    elif action == "reject":
        apply_item.status = "reject"
        flash("已驳回申请")
    db.session.commit()
    return redirect(url_for('share_page'))
# 我的全部申请记录页面（所有状态都展示，自带删除按钮）
@app.route('/share_my_apply')
@login_required
def share_my_apply():
    # 查询当前用户所有申请，按提交时间倒序
    my_all_apply = ShareApply.query.filter_by(applicant_id=current_user.id).order_by(ShareApply.create_time.desc()).all()
    return render_template("share_my_apply.html", apply_list=my_all_apply)
# 删除本人申请记录路由
@app.route('/share_apply_del/<int:aid>', methods=["POST"])
@login_required
def share_apply_del(aid):
    ap = ShareApply.query.get_or_404(aid)
    # 只能删除自己提交的申请
    if ap.applicant_id != current_user.id:
        flash("只能删除自己提交的申请记录")
        return redirect(url_for('share_my_apply'))
    db.session.delete(ap)
    db.session.commit()
    flash("申请记录已删除")
    return redirect(url_for('share_my_apply'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
