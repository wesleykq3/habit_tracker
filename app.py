from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
from datetime import date

app = Flask(__name__)
CORS(app)

# 初始化数据库
def init_db():
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS habits
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  target_days INTEGER DEFAULT 7,
                  created_date TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS completions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  habit_id INTEGER NOT NULL,
                  complete_date TEXT NOT NULL,
                  FOREIGN KEY(habit_id) REFERENCES habits(id),
                  UNIQUE(habit_id, complete_date))''')
    conn.commit()
    conn.close()

# 主页 - 返回前端页面
@app.route('/')
def index():
    return render_template('index.html')

# 获取所有习惯
@app.route('/api/habits', methods=['GET'])
def get_habits():
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    habits = c.execute('SELECT id, name, target_days FROM habits ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([{'id': h[0], 'name': h[1], 'targetDays': h[2]} for h in habits])

# 添加习惯
@app.route('/api/habits', methods=['POST'])
def add_habit():
    data = request.json
    name = data.get('name')
    target_days = data.get('targetDays', 7)
    if not name:
        return jsonify({'error': 'Name required'}), 400
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('INSERT INTO habits (name, target_days, created_date) VALUES (?, ?, ?)',
              (name, target_days, date.today().isoformat()))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return jsonify({'id': new_id, 'name': name, 'targetDays': target_days}), 201

# 删除习惯（同时删除相关的打卡记录）
@app.route('/api/habits/<int:habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('DELETE FROM completions WHERE habit_id = ?', (habit_id,))
    c.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'deleted'})

# 打卡（标记某习惯在某天完成）
@app.route('/api/completions', methods=['POST'])
def add_completion():
    data = request.json
    habit_id = data.get('habitId')
    complete_date = data.get('date', date.today().isoformat())
    if not habit_id:
        return jsonify({'error': 'habitId required'}), 400
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO completions (habit_id, complete_date) VALUES (?, ?)',
                  (habit_id, complete_date))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False  # 已经打过卡
    conn.close()
    return jsonify({'success': success})

# 取消打卡
@app.route('/api/completions', methods=['DELETE'])
def remove_completion():
    data = request.json
    habit_id = data.get('habitId')
    complete_date = data.get('date', date.today().isoformat())
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('DELETE FROM completions WHERE habit_id = ? AND complete_date = ?',
              (habit_id, complete_date))
    conn.commit()
    deleted = c.rowcount > 0
    conn.close()
    return jsonify({'deleted': deleted})

# 获取某个习惯在指定月份的所有打卡日期（用于前端显示日历/进度）
@app.route('/api/completions/<int:habit_id>', methods=['GET'])
def get_completions(habit_id):
    year_month = request.args.get('month')  # 格式 '2025-01'
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    if year_month:
        c.execute('SELECT complete_date FROM completions WHERE habit_id = ? AND complete_date LIKE ?',
                  (habit_id, year_month + '%'))
    else:
        c.execute('SELECT complete_date FROM completions WHERE habit_id = ?', (habit_id,))
    dates = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify(dates)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)