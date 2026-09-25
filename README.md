# meeting_room_booking
# 会议室预约系统（Flask）
基于 Flask + Flask-SQLAlchemy + Flask-Login 开发的会议室预约Web系统，部署于 PythonAnywhere。

## 项目目录结构
meeting_room_booking/
├── app.py                 # 后端主程序，路由、数据库模型、权限逻辑
├── instance/
│   └── room.db            # SQLite数据库文件（自动生成）
└── templates/             # 前端HTML页面
    ├── admin.html
    ├── admin_all_booking.html   # 管理员：全部预约记录，支持筛选
    ├── admin_dashboard.html     # 管理员数据看板
    ├── admin_room.html          # 管理员会议室管理（新增/删除会议室）
    ├── admin_user.html          # 管理员用户管理（角色切换、删除、密码修改）
    ├── index.html               # 首页：会议室预约、查看当日预约
    ├── login.html               # 用户登录页面
    └── register.html            # 用户注册页面

## 功能清单
### 普通用户
1. 注册账号、登录系统
2. 选择会议室与日期，提交预约（自动校验时间段冲突）
3. 查看所选日期的预约列表

### 管理员（admin角色）
1. 会议室管理：新增、删除会议室
2. 用户管理：
    - 提升/降级用户角色（普通用户 ↔ 管理员，不能修改自己权限）
    - 删除用户账号（不能删除自己）
    - 修改密码（两种方式）
        - 自定义新密码
        - 一键重置密码为 123456
    - 权限约束：管理员不能修改其他管理员的密码，仅可修改自己和普通用户密码
3. 全部预约管理：查看所有预约，按会议室、日期、预约人筛选
4. 数据看板：统计当日预约、总预约、用户、会议室数量
5. 删除任意预约记录

## 环境依赖
Flask
Flask-SQLAlchemy
Flask-Login
安装命令：
pip install flask flask-sqlalchemy flask-login

## 本地运行
1. 确保依赖已安装
2. 运行主程序
python app.py
3. 访问 http://127.0.0.1:5000
首次运行会自动创建 SQLite 数据库 instance/room.db

## PythonAnywhere 部署说明
1. 项目路径：/home/3038913903/meeting_room_booking/
2. HTML文件全部放在 templates 文件夹内
3. 网页文件更新后，在Web页面点击Reload重启服务，修改才会生效
4. 数据库文件 room.db 存放在 instance 目录

## 账号密码说明
- 密码明文存储（简易版本，生产环境建议使用bcrypt加密）
- 管理员重置密码默认值：123456

## 关键逻辑说明
1. 预约冲突检测：通过is_time_overlap函数判断时间段重叠，禁止冲突预约
2. 首页预约排序：按预约开始时间升序展示
3. 权限控制：所有管理员接口加current_user.role == "admin"校验，非管理员无法访问
4. 用户管理页面自动隐藏其他管理员的密码修改控件，防止越权

## 注意事项
1. 管理员无法修改其他管理员的密码，页面直接隐藏输入框与按钮
2. 管理员可以修改自己的密码，修改错误会导致无法登录，需要手动修改数据库
3. 权限操作（改角色、删账号）禁止作用于当前登录管理员自身
4. 时间校验：不允许预约过去的时间

## 备注
1. 点击这个黄色按钮，就能**把你的 Flask 会议室预约网站再续一个月**，网站不会下线；
2. 免费版规则：**必须每月点一次续期**，不然到期网站直接关停，别人就打不开你的项目网址了；
3. 系统会在到期前一周给你的注册邮箱发提醒。
4. 点击“Run until 1 month from today”后记得点击绿色按钮“Reload 3038913903.pythonanywhere.com”重新加载（重启 Web 服务）
<img width="1307" height="517" alt="image" src="https://github.com/user-attachments/assets/52e7e98c-8427-409a-90bc-958479011a49" />
