import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import hashlib
import extra_streamlit_components as stx
import datetime

# --- 页面设置 ---
st.set_page_config(page_title="通用投资决策仪表盘", page_icon="icon.png", layout="wide")

# ==========================================
#        0. 云端多用户记忆引擎 (含加密)
# ==========================================
API_KEY = st.secrets["JSONBIN_KEY"]
BIN_ID = st.secrets["JSONBIN_ID"]
URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
HEADERS = {"X-Master-Key": API_KEY, "Content-Type": "application/json"}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_all_cloud_data():
    try:
        response = requests.get(URL, headers=HEADERS)
        data = response.json().get("record", {})
        if "users" not in data: data["users"] = {}
        if "watchlists" not in data: data["watchlists"] = {}
        return data
    except Exception:
        return {"users": {}, "watchlists": {}}

def save_to_cloud(all_data):
    try:
        requests.put(URL, json=all_data, headers=HEADERS)
    except Exception as e:
        st.error(f"⚠️ 云端同步失败: {e}")

def get_category(symbol):
    symbol = str(symbol).strip().upper()
    if symbol.endswith(".SZ") or symbol.endswith(".SS"):
        if symbol.startswith("15") or symbol.startswith("51"): return "📊 国内 ETF"
        else: return "🇨🇳 A股个股"
    elif symbol.endswith(".HK"): return "🇭🇰 港股"
    elif symbol.isalpha(): return "🇺🇸 美股"
    else: return "🌍 其他标的"

# ==========================================
#        1. 登录与注册验证系统 (修复版)
# ==========================================
# 💡 彻底修复警告：不再放入缓存盒子，直接初始化并赋予唯一 Key
cookie_manager = stx.CookieManager(key="my_cookie_manager")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = ""

# 读取浏览器 Cookie，判断是否免密登录
saved_user = cookie_manager.get(cookie="saved_user")
if saved_user and not st.session_state.logged_in:
    st.session_state.logged_in = True
    st.session_state.current_user = saved_user

# 登录与注册界面
if not st.session_state.logged_in:
    st.title("🔐 通用投资决策仪表盘")
    st.markdown("请先登录或注册您的专属云端账号。")
    
    tab_login, tab_register = st.tabs(["🔑 账号登录", "📝 注册新账号"])
    
    with tab_login:
        with st.form("login_form"):
            login_user = st.text_input("用户名")
            login_pwd = st.text_input("密码", type="password")
            remember_me = st.checkbox("记住我 (30天免登录)", value=True)
            submit_login = st.form_submit_button("登录", type="primary")
            
            if submit_login:
                db = load_all_cloud_data()
                if login_user in db["users"] and db["users"][login_user] == hash_password(login_pwd):
                    st.session_state.logged_in = True
                    st.session_state.current_user = login_user
                    
                    if remember_me:
                        expire_date = datetime.datetime.now() + datetime.timedelta(days=30)
                        cookie_manager.set("saved_user", login_user, expires_at=expire_date)
                        
                    st.success("登录成功！正在进入您的专属空间...")
                    st.rerun()
                else:
                    st.error("❌ 用户名或密码错误，请重试。")
                    
    with tab_register:
        with st.form("register_form"):
            reg_user = st.text_input("设置用户名 (不少于3个字符)")
            reg_pwd = st.text_input("设置密码 (不少于6个字符)", type="password")
            reg_pwd_confirm = st.text_input("确认密码", type="password")
            submit_register = st.form_submit_button("注册并登录")
            
            if submit_register:
                if len(reg_user) < 3 or len(reg_pwd) < 6 or reg_pwd != reg_pwd_confirm:
                    st.error("请检查输入要求或确认密码是否一致！")
                else:
                    db = load_all_cloud_data()
                    if reg_user in db["users"]:
                        st.error("❌ 该用户名已被注册。")
                    else:
                        db["users"][reg_user] = hash_password(reg_pwd)
                        db["watchlists"][reg_user] = {}
                        save_to_cloud(db)
                        
                        st.session_state.logged_in = True
                        st.session_state.current_user = reg_user
                        
                        expire_date = datetime.datetime.now() + datetime.timedelta(days=30)
                        cookie_manager.set("saved_user", reg_user, expires_at=expire_date)
                        
                        st.success("✅ 注册成功！")
                        st.rerun()
    st.stop()

# ==========================================
#        2. 主程序 (仅登录后可见)
# ==========================================
st.sidebar.title(f"👋 欢迎回来, {st.session_state.current_user}")

if st.sidebar.button("🚪 退出登录"):
    st
