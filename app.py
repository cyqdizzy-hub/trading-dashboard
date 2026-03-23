import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 页面设置 ---
st.set_page_config(page_title="通用投资决策仪表盘", page_icon="📈", layout="wide")

# --- 1. 初始化会话状态 ---
if 'current_price' not in st.session_state:
    st.session_state.current_price = 0.0
if 'df_history' not in st.session_state:
    st.session_state.df_history = pd.DataFrame()

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = {
        "159934.SZ": {"cost": 8.592, "qty": 3776}, 
        "513100.SS": {"cost": 1.200, "qty": 1000}  
    }

# 初始化当前选中的标的记录
if 'sidebar_select' not in st.session_state:
    st.session_state.sidebar_select = "159934.SZ"

# --- 2. 侧边栏：直观导航列表 ---
st.sidebar.title("⭐ 我的自选库")

# 顶部的“新建”按钮
if st.sidebar.button("➕ 手动输入新标的", type="primary" if st.session_state.sidebar_select == "" else "secondary", use_container_width=True):
    st.session_state.sidebar_select = ""
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown("**已收藏列表 (点击切换)：**")

# 💡 核心升级：动态生成带删除按钮的列表
for symbol, data in list(st.session_state.watchlist.items()):
    # 将侧边栏划分为两列：左边宽（放名字），右边窄（放删除键）
    col1, col2 = st.sidebar.columns([4, 1])
    
    # 当前选中的标的，按钮会变成蓝色(primary)高亮显示
    btn_type = "primary" if st.session_state.sidebar_select == symbol else "secondary"
    
    # 点击标的名字，立刻切换为主视图
    if col1.button(f"📊 {symbol}", key=f"sel_{symbol}", type=btn_type, use_container_width=True):
        st.session_state.sidebar_select = symbol
        st.rerun()
        
    # 点击旁边的垃圾桶，立刻删除
    if col2.button("🗑️", key=f"del_{symbol}", help=f"删除 {symbol}"):
        del st.session_state.watchlist[symbol]
        # 如果删掉的是当前正在看的，就清空主界面
        if st.session_state.sidebar_select == symbol:
            st.session_state.sidebar_select = ""
        st.rerun()

# 根据当前选中的状态，填充右侧主界面的默认值
if st.session_state.sidebar_select and st.session_state.sidebar_select in st.session_state.watchlist:
    default_sym = st.session_state.sidebar_select
    default_cost = float(st.session_state.watchlist[default_sym]['cost'])
    default_qty = int(st.session_state.watchlist[default_sym]['qty'])
else:
    default_sym = ""
    default_cost = 0.0
    default_qty = 0

st.sidebar.divider()
st.sidebar.markdown("💡 **提示：** 在右侧主界面输入新的代码和持仓后，点击下方保存按钮即可加入此列表。")

# --- 3. 数据抓取与指标计算函数 ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data_and_calc_ind(symbol):
    try:
        df = yf.download(symbol, period="1y", progress=False, threads=False)
        if df is None or len(df) == 0:
            return None, "云端服务器IP正处于限制期，请稍后再试或换用本地电脑运行。"
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        return df.iloc[-126:], "成功"
    except Exception as e:
        return None, str(e)

# --- 4. K 线图绘制函数 ---
def plot_candlestick(df, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_width=[0.2, 0.8])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K线', increasing_line_color='#ef5350', decreasing_line_color='#26a69a'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日线', line=dict(color='#ffca28', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60日线', line=dict(color='#2196f3', width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='#90caf9'), row=2, col=1)
    fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# ==========================================
#                  主界面构建
# ==========================================
st.title("📈 通用投资决策仪表盘")

# 1. 顶部：联动输入区
with st.container():
    c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1.5])
    
    with c1: 
        input_symbol = st.text_input("🔍 标的代码", value=default_sym, help="深市:.SZ, 沪市:.SS, 美股直接输")
    with c2: 
        input_cost = st.number_input("底仓成本", value=default_cost, step=0.01)
    with c3: 
        input_qty = st.number_input("持仓数量", value=default_qty, step=100)
    
    with c4:
        st.write("") 
        if st.button("🔄 同步K线与现价", type="primary", use_container_width=True):
            if input_symbol:
                with st.spinner(f'正在同步 {input_symbol} ...'):
                    df_h, msg = fetch_data_and_calc_ind(input_symbol)
                    if df_h is not None:
                        st.session_state.df_history = df_h
                        st.session_state.current_price = float(df_h.iloc[-1]['Close'])
                    else:
                        st.error(f"❌ 获取失败：{msg}")

# --- 保存自选动作 ---
if st.button("💾 将当前输入的内容保存/更新至左侧列表"):
    if input_symbol:
        st.session_state.watchlist[input_symbol] = {"cost": input_cost, "qty": input_qty}
        st.session_state.sidebar_select = input_symbol 
        st.success(f"✅ {input_symbol} 已成功保存！")
        st.rerun() 

st.divider()

# 2. 中部：K 线图展示
if not st.session_state.df_history.empty and st.session_state.current_price > 0:
    fig_k = plot_candlestick(st.session_state.df_history, input_symbol)
    st.plotly_chart(fig_k, use_container_width=True)
else:
    st.info("💡 请在上方确认代码后，点击“同步K线与现价”。")

st.divider()

# 3. 底部：加仓推演 
if not st.session_state.df_history.empty and st.session_state.current_price > 0:
    col_calc, col_adv = st.columns([1, 1.2], gap="large")
    
    with col_calc:
        st.subheader("⚙️ 动态加仓推演")
        st.metric("最新现价", f"¥ {st.session_state.current_price:.3f}")
        
        qty_add = st.slider("计划加仓数量", min_value=0, max_value=int(max(input_qty * 2, 1000)), value=0, step=100)
        
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
        st.subheader("🤖 智能决策建议")
        df = st.session_state.df_history
        ma20, ma60 = df.iloc[-1]['MA20'], df.iloc[-1]['MA60']
        
        if current_p > ma60 and ma20 > ma60:
            st.success("📈 **多头趋势**：价格站上60日均线。")
            if 0 < (current_p - ma20)/ma20 < 0.02:
                st.success("🎯 **绝佳买点**：已回调至20日线附近，支撑较强。")
            elif (current_p - ma20)/ma20 >= 0.02:
                st.warning("⏳ **注意追高**：偏离20日线较远，建议等待回调。")
        elif current_p < ma60:
            st.error("📉 **空头/调整趋势**：已跌破60日生命线，严禁盲目加仓，等待企稳。")
        else:
            st.info("⚖️ **震荡整理**：趋势不清晰，多看少动。")
            
        if qty_add > 0:
            st.markdown("---")
            st.markdown(f"**🛡️ 本次加仓防守线：** 若跌破 20日线 ({ma20:.3f}) 平掉新仓；若跌破新成本线 ({new_cost:.3f}) 彻底清仓保本。")
