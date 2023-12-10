




## 项目概述

这个 Django 项目是一个空调控制系统，用于管理和控制空调设备。它允许用户通过一个 web 界面来控制空调的各种功能，如温度调节、风速设置、开关机等。该系统还包括管理员和前台操作界面，用于系统设置和客户服务。

## 目录
```
├── BUPT_AC_Hotel
│   ├── AC
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── migrations
│   │   ├── models.py
│   │   ├── test.py
│   │   └── views.py
│   ├── BUPT_Hotel
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── manage.py
│   ├── static
│   │   └── css
│   ├── statics
│   │   ├── css
│   │   └── js
│   ├── tempCodeRunnerFile.python
│   └── templates
│       ├── client-off.html
│       ├── client-on.html
│       ├── guanli_login.html
│       ├── index.html
│       ├── init.html
│       ├── login.html
│       ├── monitor.html
│       ├── reception.html
│       └── report.html
```

## 系统要求

- Python 3.11
- Django 4.1


## 安装与运行

1. **克隆仓库**:
   ```bash
   git clone https://github.com/abinzzz/BUPT_AC_Hotel.git
   ```



2. **数据库迁移**:
   执行以下命令来迁移数据库：
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **运行服务器**:
   ```bash
   python manage.py runserver
   ```

4. 在浏览器中打开 `http://localhost:8000/` 来访问项目。

## 功能概述

### 客户端

- **开机/关机**: 用户可以通过客户端界面开启或关闭空调。
- **调节温度**: 提供升温和降温功能。
- **调节风速**: 支持高、中、低三种风速设置。

### 管理员

- **系统设置**: 管理员可以初始化系统设置，如温度限制、费率等。
- **监控**: 查看当前所有房间的状态。

### 前台接待

- **详单和账单**: 前台可以为客户打印详单和账单。

### 经理

- **报表**: 经理可以生成和查看月报和周报。

## 注意事项

确保在开始之前已正确配置数据库和其他依赖项。

