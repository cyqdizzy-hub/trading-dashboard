import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import hashlib

# --- 页面设置 ---
st.set_page_config(page_title="通用投资决策仪表盘 2.0", page_icon="icon.png", layout="wide")

# ==========================================
#        0. 云端多用户记忆引擎
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
#        1. 登录与注册验证系统
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'current_user' not in st.session_state: st.session_state.current_user = ""

if not st.session_state.logged_in:
    st.title("🔐 通用投资决策仪表盘")
    st.markdown("请先登录或注册您的专属云端账号。")
    tab_login, tab_register = st.tabs(["🔑 账号登录", "📝 注册新账号"])
    
    with tab_login:
        with st.form("login_form"):
            login_user = st.text_input("用户名")
            login_pwd = st.text_input("密码", type="password")
            if st.form_submit_button("登录", type="primary"):
                db = load_all_cloud_data()
                if login_user in db["users"] and db["users"][login_user] == hash_password(login_pwd):
                    st.session_state.logged_in = True
                    st.session_state.current_user = login_user
                    st.success("登录成功！正在进入您的专属空间...")
                    st.rerun()
                else:
                    st.error("❌ 用户名或密码错误。")
                    
    with tab_register:
        with st.form("register_form"):
            reg_user = st.text_input("设置用户名 (不少于3个字符)")
            reg_pwd = st.text_input("设置密码 (不少于6个字符)", type="password")
            reg_pwd_confirm = st.text_input("确认密码", type="password")
            if st.form_submit_button("注册并登录"):
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
                        st.success("✅ 注册成功！")
                        st.rerun()
    st.stop()

# ==========================================
#        2. 主程序 (仅登录后可见)
# ==========================================
st.sidebar.title(f"👋 欢迎回来, {st.session_state.current_user}")
if st.sidebar.button("🚪 退出登录"):
    st.session_state.logged_in = False
    st.session_state.current_user = ""
    st.rerun()
st.sidebar.divider()

if 'watchlist' not in st.session_state or st.session_state.get('last_user') != st.session_state.current_user:
    all_users_data = load_all_cloud_data()
    st.session_state.watchlist = all_users_data["watchlists"].get(st.session_state.current_user, {})
    st.session_state.last_user = st.session_state.current_user
    st.session_state.sidebar_select = ""

if 'current_price' not in st.session_state: st.session_state.current_price = 0.0
if 'df_history' not in st.session_state: st.session_state.df_history = pd.DataFrame()
if 'current_pe' not in st.session_state: st.session_state.current_pe = None

if st.sidebar.button("➕ 手动输入新标的", type="primary" if st.session_state.sidebar_select == "" else "secondary", use_container_width=True):
    st.session_state.sidebar_select = ""
    st.rerun()

st.sidebar.divider()

categories_dict = {}
for sym, data in st.session_state.watchlist.items():
    cat = data.get('category', '🌍 其他标的')
    if cat not in categories_dict: categories_dict[cat] = []
    categories_dict[cat].append((sym, data))

for cat, items in categories_dict.items():
    st.sidebar.caption(f"**{cat}**") 
    for sym, data in items:
        col1, col2 = st.sidebar.columns([4, 1])
        btn_type = "primary" if st.session_state.sidebar_select == sym else "secondary"
        display_name = data.get('name', '')
        btn_label = f"{display_name} ({sym})" if display_name else f"📊 {sym}"
        if col1.button(btn_label, key=f"sel_{sym}", type=btn_type, use_container_width=True):
            st.session_state.sidebar_select = sym
            st.rerun()
        if col2.button("🗑️", key=f"del_{sym}", help=f"删除 {sym}"):
            del st.session_state.watchlist[sym]
            db = load_all_cloud_data()
            db["watchlists"][st.session_state.current_user] = st.session_state.watchlist
            save_to_cloud(db)
            if st.session_state.sidebar_select == sym: st.session_state.sidebar_select = ""
            st.rerun()
    st.sidebar.write("")

if st.session_state.sidebar_select and st.session_state.sidebar_select in st.session_state.watchlist:
    default_sym = st.session_state.sidebar_select
    default_data = st.session_state.watchlist[default_sym]
    default_name = default_data.get('name', '')
    default_cost = float(default_data.get('cost', 0.0))
    default_qty = int(default_data.get('qty', 0))
else:
    default_sym, default_name, default_cost, default_qty = "", "", 0.0, 0

# 💡 核心升级：获取更多维度的数据 (含 MACD, 量能与 PE)
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data_and_calc_ind(symbol):
    try:
        # 获取 K 线数据
        df = yf.download(symbol, period="1y", progress=False, threads=False)
        if df is None or len(df) == 0: return None, None, "获取数据失败，请检查代码格式是否正确。"
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. 均线系统
        df['MA20'], df['MA60'] = df['Close'].rolling(window=20).mean(), df['Close'].rolling(window=60).mean()
        
        # 2. 量能均线 (5日平均成交量)
        df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
        
        # 3. MACD 指标手搓计算
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['Signal']

        # 4. 获取基本面 PE (市盈率)
        try:
            ticker_info = yf.Ticker(symbol).info
            pe_ratio = ticker_info.get('trailingPE', ticker_info.get('forwardPE', None))
        except:
            pe_ratio = None
            
        return df.iloc[-126:], pe_ratio, "成功"
    except Exception as e: return None, None, str(e)

def plot_candlestick(df, symbol, name):
    title = f"{name} ({symbol}) - 6个月日K线图" if name else f"{symbol} - 6个月日K线图"
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.8], subplot_titles=(title, '成交量'))
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日线', line=dict(color='#ffca28', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60日线', line=dict(color='#2196f3', width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='#90caf9'), row=2, col=1)
    fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

st.title("📈 通用投资决策仪表盘 2.0")
ui_key = default_sym if default_sym else "new_entry"

with st.container():
    c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1, 1.2])
    with c1: input_symbol = st.text_input("🔍 标的代码", value=default_sym, key=f"sym_{ui_key}", help="深市:.SZ, 沪市:.SS, 美股直接输")
    with c2: input_name = st.text_input("🏷️ 标的名称", value=default_name, key=f"name_{ui_key}")
    with c3: input_cost = st.number_input("底仓成本", value=default_cost, step=0.01, key=f"cost_{ui_key}")
    with c4: input_qty = st.number_input("持仓数量", value=default_qty, step=100, key=f"qty_{ui_key}")
    
    with c5:
        st.write("") 
        if st.button("🔄 同步K线与现价", type="primary", use_container_width=True):
            if input_symbol:
                with st.spinner(f'正在深度解析 {input_symbol} 的量价与基本面...'):
                    df_h, pe_val, msg = fetch_data_and_calc_ind(input_symbol)
                    if df_h is not None:
                        st.session_state.df_history = df_h
                        st.session_state.current_price = float(df_h.iloc[-1]['Close'])
                        st.session_state.current_pe = pe_val
                    else:
                        st.error(f"❌ 获取失败：{msg}")

if st.button("💾 将当前标的保存/更新至专属空间"):
    if input_symbol:
        st.session_state.watchlist[input_symbol] = {
            "name": input_name, "cost": input_cost, "qty": input_qty, "category": get_category(input_symbol) 
        }
        db = load_all_cloud_data()
        db["watchlists"][st.session_state.current_user] = st.session_state.watchlist
        save_to_cloud(db)
        st.session_state.sidebar_select = input_symbol 
        st.success("✅ 已成功保存！")
        st.rerun() 

st.divider()

if not st.session_state.df_history.empty and st.session_state.current_price > 0:
    fig_k = plot_candlestick(st.session_state.df_history, input_symbol, input_name)
    st.plotly_chart(fig_k, use_container_width=True)

    st.divider()
    col_calc, col_adv = st.columns([1, 1.2], gap="large")
    
    with col_calc:
        st.subheader("⚙️ 动态加仓推演")
        st.metric("最新现价", f"¥ {st.session_state.current_price:.3f}")
        qty_add = st.slider("计划加仓数量", min_value=0, max_value=int(max(input_qty * 2, 1000)), value=0, step=100, key=f"slider_{ui_key}")
        total_qty = input_qty + qty_add
        current_p = st.session_state.current_price
        
        if total_qty > 0:
            new_cost = ((input_cost * input_qty) + (current_p * qty_add)) / total_qty
            safe_cushion = ((current_p - new_cost) / current_p) * 100 if current_p > 0 else 0
        else:
            new_cost, safe_cushion = input_cost, 0

        r1, r2 = st.columns(2)
        r1.metric("加仓后新保本点", f"{new_cost:.3f}", f"成本抬升 {new_cost-input_cost:.3f}" if qty_add > 0 else None, delta_color="inverse")
        r2.metric("利润安全垫", f"{safe_cushion:.2f}%")

    with col_adv:
        st.subheader("🤖 智能决策建议 (多维共振)")
        df = st.session_state.df_history
        ma20, ma60 = df.iloc[-1]['MA20'], df.iloc[-1]['MA60']
        
        # 1. 均线趋势判定
        if current_p > ma60 and ma20 > ma60:
            st.success(f"📈 **主趋势：** 站上 60 日线，**多头格局**。")
            if 0 < (current_p - ma20)/ma20 < 0.02: st.caption("🎯 距 20 日线极近，短线防守性价比高。")
            elif (current_p - ma20)/ma20 >= 0.03: st.caption("⏳ 偏离 20 日均线较远，严防冲高回落。")
        elif current_p < ma60:
            st.error(f"📉 **主趋势：** 跌破 60 日线，**空头/调整格局**，忌盲目抄底。")
        else:
            st.info(f"⚖️ **主趋势：** 震荡整理，趋势不清晰。")

        # 2. 量能异动判定
        vol, vol_ma5 = df.iloc[-1]['Volume'], df.iloc[-1]['Vol_MA5']
        if vol > vol_ma5 * 2:
            st.warning(f"🔥 **资金面：** 今日**放量异动** (超5日均量2倍)！若为突破则看多，若在高位需防出货。")
        elif vol < vol_ma5 * 0.5:
            st.info(f"🧊 **资金面：** 今日**极致缩量**，面临方向变盘选择。")
            
        # 3. MACD 动能判定 (取最后两天的柱子对比)
        hist, prev_hist = df.iloc[-1]['MACD_Hist'], df.iloc[-2]['MACD_Hist']
        if hist > 0 and prev_hist <= 0:
            st.success(f"✨ **动能面：** MACD 刚刚形成 **金叉**，短线做多动能增强！")
        elif hist < 0 and prev_hist >= 0:
            st.error(f"⚠️ **动能面：** MACD 刚刚形成 **死叉**，短线空头释放，警惕回调！")

        # 4. 基本面估值判定
        pe_val = st.session_state.current_pe
        pe_text = "未知 (可能为ETF或数据缺失)" if pe_val is None else f"{pe_val:.2f}"
        st.markdown(f"**🏢 估值面 (动态PE):** {pe_text}")
        if pe_val:
            if pe_val < 15: st.caption("🟢 当前估值较低具备较高安全边际 (仅供参考)。")
            elif pe_val > 30: st.caption("🔴 当前估值偏高，注意成长性是否能消化高估值风险。")

else:
    st.info("💡 请在上方确认代码后，点击“同步K线与现价”。")
