# -*- coding: utf-8 -*-
"""
婴儿健康记录系统 - Baby Record System
婴儿：小彭 | 出生日期：2026-07-08
"""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import pandas as pd
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for
import plotly.graph_objects as go
from plotly.subplots import make_subplots

app = Flask(__name__)

# 配置
BABY_NAME = "小彭"
BABY_BIRTHDAY = datetime(2025, 7, 8).date()
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FEEDING_FILE = os.path.join(DATA_DIR, "feeding.csv")
GROWTH_FILE = os.path.join(DATA_DIR, "growth.csv")

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 初始化 CSV 文件
if not os.path.exists(FEEDING_FILE):
    df = pd.DataFrame(columns=["date", "time", "type", "amount_ml", "notes"])
    df.to_csv(FEEDING_FILE, index=False, encoding="utf-8")

if not os.path.exists(GROWTH_FILE):
    df = pd.DataFrame(columns=["date", "height_cm", "weight_kg", "head_circumference_cm", "notes"])
    df.to_csv(GROWTH_FILE, index=False, encoding="utf-8")


def get_age_months(check_date=None):
    """计算月龄"""
    if check_date is None:
        check_date = date.today()
    if check_date < BABY_BIRTHDAY:
        return 0
    months = (check_date.year - BABY_BIRTHDAY.year) * 12 + (check_date.month - BABY_BIRTHDAY.month)
    return months


@app.route("/")
def index():
    """主页"""
    # 读取数据
    feeding_df = pd.read_csv(FEEDING_FILE)
    growth_df = pd.read_csv(GROWTH_FILE)
    
    # 转换日期
    feeding_df["date"] = pd.to_datetime(feeding_df["date"])
    growth_df["date"] = pd.to_datetime(growth_df["date"])
    
    # 计算统计数据
    total_feedings = len(feeding_df)
    total_milk = feeding_df["amount_ml"].sum() if total_feedings > 0 else 0
    
    # 喂养方式统计
    feeding_type_counts = feeding_df.groupby("type")["amount_ml"].sum().to_dict()
    
    # 最新生长发育数据
    latest_growth = growth_df.iloc[-1].to_dict() if len(growth_df) > 0 else None
    if latest_growth and 'date' in latest_growth:
        latest_growth['date'] = str(latest_growth['date'])
    
    # 转换日期为字符串
    feeding_records = feeding_df.tail(10).to_dict("records")
    for r in feeding_records:
        if 'date' in r:
            r['date'] = str(r['date'])
        if 'time' not in r or pd.isna(r.get('time')):
            r['time'] = ""
    
    growth_records = growth_df.tail(10).to_dict("records")
    for r in growth_records:
        if 'date' in r:
            r['date'] = str(r['date'])
    
    return render_template(
        "index.html",
        baby_name=BABY_NAME,
        baby_birthday=BABY_BIRTHDAY,
        age_months=get_age_months(),
        total_feedings=total_feedings,
        total_milk=total_milk,
        feeding_type_counts=feeding_type_counts,
        latest_growth=latest_growth,
        feeding_df=feeding_records,
        growth_df=growth_records
    )


@app.route("/add_feeding", methods=["POST"])
def add_feeding():
    """添加喂养记录"""
    date_str = request.form.get("date")
    time_str = request.form.get("time", "00:00")
    feeding_type = request.form.get("type")
    amount = float(request.form.get("amount_ml", 0))
    notes = request.form.get("notes", "")
    
    # 读取现有数据
    df = pd.read_csv(FEEDING_FILE)
    
    # 添加新记录
    new_record = {
        "date": date_str,
        "time": time_str,
        "type": feeding_type,
        "amount_ml": amount,
        "notes": notes
    }
    df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    
    # 保存
    df.to_csv(FEEDING_FILE, index=False, encoding="utf-8")
    
    return redirect(url_for("index"))


@app.route("/add_growth", methods=["POST"])
def add_growth():
    """添加生长发育记录"""
    date_str = request.form.get("date")
    height = float(request.form.get("height_cm", 0))
    weight = float(request.form.get("weight_kg", 0))
    head_circ = float(request.form.get("head_circumference_cm", 0))
    notes = request.form.get("notes", "")
    
    # 读取现有数据
    df = pd.read_csv(GROWTH_FILE)
    
    # 添加新记录
    new_record = {
        "date": date_str,
        "height_cm": height,
        "weight_kg": weight,
        "head_circumference_cm": head_circ,
        "notes": notes
    }
    df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    
    # 保存
    df.to_csv(GROWTH_FILE, index=False, encoding="utf-8")
    
    return redirect(url_for("index"))


@app.route("/charts")
def charts():
    """统计图表页面"""
    # 读取数据
    feeding_df = pd.read_csv(FEEDING_FILE)
    growth_df = pd.read_csv(GROWTH_FILE)
    
    feeding_df["date"] = pd.to_datetime(feeding_df["date"])
    growth_df["date"] = pd.to_datetime(growth_df["date"])
    
    # 1. 喂养量趋势图
    daily_feeding = feeding_df.groupby("date")["amount_ml"].sum().reset_index()
    feeding_trend = go.Figure()
    feeding_trend.add_trace(go.Scatter(
        x=daily_feeding["date"], 
        y=daily_feeding["amount_ml"],
        mode="lines+markers",
        name="每日喂养量",
        line=dict(color="#3498db", width=2),
        marker=dict(size=8)
    ))
    feeding_trend.update_layout(
        title="每日喂养量趋势",
        xaxis_title="日期",
        yaxis_title="喂养量 (ml)",
        template="plotly_white"
    )
    feeding_trend_html = feeding_trend.to_html(full_html=False, include_plotlyjs=False)
    
    # 2. 喂养方式占比饼图
    feeding_type_sum = feeding_df.groupby("type")["amount_ml"].sum()
    feeding_pie = go.Figure(data=[go.Pie(
        labels=feeding_type_sum.index,
        values=feeding_type_sum.values,
        hole=0.4,
        marker=dict(colors=["#e74c3c", "#3498db", "#2ecc71"])
    )])
    feeding_pie.update_layout(title="喂养方式占比", template="plotly_white")
    feeding_pie_html = feeding_pie.to_html(full_html=False, include_plotlyjs=False)
    
    # 3. 生长发育曲线
    if len(growth_df) > 0:
        growth_chart = make_subplots(
            rows=1, cols=3,
            subplot_titles=("身高曲线", "体重曲线", "头围曲线"),
            horizontal_spacing=0.1
        )
        
        # 身高
        growth_chart.add_trace(
            go.Scatter(x=growth_df["date"], y=growth_df["height_cm"], 
                      mode="lines+markers", name="身高", line=dict(color="#9b59b6")),
            row=1, col=1
        )
        
        # 体重
        growth_chart.add_trace(
            go.Scatter(x=growth_df["date"], y=growth_df["weight_kg"],
                      mode="lines+markers", name="体重", line=dict(color="#e67e22")),
            row=1, col=2
        )
        
        # 头围
        growth_chart.add_trace(
            go.Scatter(x=growth_df["date"], y=growth_df["head_circumference_cm"],
                      mode="lines+markers", name="头围", line=dict(color="#1abc9c")),
            row=1, col=3
        )
        
        growth_chart.update_layout(
            title="生长发育曲线",
            showlegend=True,
            template="plotly_white"
        )
        growth_chart_html = growth_chart.to_html(full_html=False, include_plotlyjs=False)
    else:
        growth_chart_html = "<p>暂无生长发育数据</p>"
    
    return render_template(
        "charts.html",
        feeding_trend_html=feeding_trend_html,
        feeding_pie_html=feeding_pie_html,
        growth_chart_html=growth_chart_html
    )


if __name__ == "__main__":
    print("Baby Record System Starting...")
    print(f"Baby: {BABY_NAME}")
    print(f"Birthday: {BABY_BIRTHDAY}")
    print("Access: http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
