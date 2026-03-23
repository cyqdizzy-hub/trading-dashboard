import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import requests # 新增：用于伪装请求

# --- 页面设置 ---
st.set_page_config(page_title="通用投资决策仪表盘", page_icon="📈", layout="wide")

# --- 初始化会话状态 ---
if 'current_price' not in st.session_state:
    st.session_state.current_price = 0.0
if 'target_symbol' not in st.session_state:
    st.session_state.target_symbol = "159934.SZ"
if 'df_history' not in st.session_state:
    st.session_state.df_history = pd.DataFrame()

# --- 1. 数据抓取与指标计算函数 (加入缓存和防屏蔽机制) ---
# 这里的 ttl=3600 表示缓存保留 1 小时，1 小时内重复查询同一代码不会重新发起网络请求
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data_and_calc_ind(symbol):
    try:
        # 建立一个伪装成浏览器的会话
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 使用伪装的会话去请求雅虎财经
        ticker = yf.Ticker(symbol, session=session)
        df = ticker.history(period="1y")
        
        if df.empty:
            return None, "未获取到数据，请检查代码格式是否正确。"
        
        # 计算技术指标
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        # 截取最近半年
        df_display = df.iloc[-126:] 
        return df_display, "成功"
    except Exception as e:
        return None, str(e)

# --- 2. 交互式 K 线图绘制函数 ---
def plot_candlestick(df, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{symbol} 6个月日K线图', '成交量'), 
                        row_width=[0.2, 0.8])

    fig.add_trace(go.Candlestick(x=df.index,
                                open=df['Open'], high=df['High'],
                                low=df['Low'], close=df['Close'],
                                name='K线',
                                increasing_line_color='#ef5350', 
                                decreasing_line_color='#26a69a'), 
                  row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日线 (短期)', line=dict(color='#ffca28', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60日线 (中期)', line=dict(color='#2196f3', width=1.5)), row=1, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='#90caf9'), row=2, col=1)

    fig.update_layout(
        xaxis_rangeslider_visible=False, 
        height=600,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="价格", row=1, col=1)
    return fig

# --- 3. 智能投资建议引擎 ---
def generate_advice(df, cost_old, qty_add, current_p):
    if df.empty or cost_old == 0:
        return "请先同步数据并输入底仓成本。", "secondary"
    
    latest = df.iloc[-1]
    ma20 = latest['MA20']
    ma60 = latest['MA60']
    
    advice = []
    status = "success" 

    st.markdown("#### ⚖️ 综合评估")
    
    if current_p > ma60 and ma20 > ma60:
        advice.append("📈 **市场环境：多头趋势**。当前处于中期上升通道中。")
        dist_to_ma20 = (current_p - ma20) / ma20
        if 0 < dist_to_ma20 < 0.02:
            advice.append("🎯 **加仓机会**：价格已回调至 20 日均线支撑位附近，性价比合理。")
        elif dist_to_ma20 > 0.05:
            advice.append("⏳ **操作建议**：偏离短期均线过远，存在追高风险。建议耐心等待回调。")
            status = "warning"
        else:
            advice.append("👀 **操作建议**：多头持有，关注支撑。")
    elif current_p < ma60:
        advice.append("📉 **市场环境：空头/调整趋势**。价格已跌破中期生命线。")
        advice.append("🛑 **操作建议**：**不宜加仓追高**。以保护底仓利润或降低风险为主。")
        status = "error"
    else:
        advice.append("⚖️ **市场环境：震荡市**。趋势不明显，多看少动。")
        status = "warning"

    if qty_add > 0:
        st.divider()
        st.markdown("#### 🛡️ 加仓风控建议")
        new_cost = ((cost_old * 3776) + (current_p * qty_add)) / (3776 + qty_add)
        if current_p < new_cost:
             advice.append("⚠️ **风控警报**：加仓后已陷入亏损！")
        
        advice.append(f"1. **短期纠错**：若有效跌破 20 日均线 ({ma20:.3f})，建议平掉新仓。")
        advice.append(f"2. **绝对保本线**：若跌破新成本线，必须无条件清仓。")

    return "\n\n".join(advice), status

# ==========================================
#                  界面构建
# ==========================================
st.title("📈 通用投资决策仪表盘")
st.markdown("输入代码 -> 查看 K 线与趋势 -> 模拟加仓 -> 获取智能风控建议。")

with st.container():
    c1, c2, c3 = st.columns([1.5, 2, 1])
    with c1:
        st.session_state.target_symbol = st.text_input("🔍 输入标的代码", value=st.session_state.target_symbol, help="深市:.SZ, 沪市:.SS, 美股:直接输")
    
    with c2:
        st.write("") 
        if st.button("🔄 同步 6个月行情与 K线", type="primary", use_container_width=True):
            with st.spinner(f'正在同步 {st.session_state.target_symbol} ...'):
                df_h, msg = fetch_data_and_calc_ind(st.session_state.target_symbol)
                if df_h is not None:
                    st.session_state.df_history = df_h
                    st.session_state.current_price = float(df_h.iloc[-1]['Close'])
                    st.toast("✅ 数据同步成功！")
                    st.rerun()
                else:
                    st.error(f"❌ 获取失败：{msg}")

    with c3:
        st.metric("最新现价", f"{st.session_state.current_price:.3f}" if st.session_state.current_price > 0 else "N/A")

st.divider()

if not st.session_state.df_history.empty:
    fig_k = plot_candlestick(st.session_state.df_history, st.session_state.target_symbol)
    st.plotly_chart(fig_k, use_container_width=True)
else:
    st.info("💡 请先在上方输入代码，点击按钮同步数据。")

st.divider()

if not st.session_state.df_history.empty:
    col_calc, col_adv = st.columns([1, 1.2], gap="large")
    
    with col_calc:
        st.subheader("⚙️ 仓位推演")
        c1, c2 = st.columns(2)
        with c1:
            cost_old = st.number_input("底仓平均成本", value=8.592, step=0.01)
        with c2:
            qty_old = st.number_input("底仓持有数量", value=3776, step=100)
        
        qty_add = st.slider("计划加仓数量", min_value=0, max_value=int(qty_old * 2), value=0, step=100)
        
        total_qty = qty_old + qty_add
        current_p = st.session_state.current_price
        if total_qty > 0:
            new_cost = ((cost_old * qty_old) + (current_p * qty_add)) / total_qty
            safe_cushion = ((current_p - new_cost) / current_p) * 100 if current_p > 0 else 0
        else:
            new_cost, safe_cushion = cost_old, 0

        r1, r2 = st.columns(2)
        r1.metric("加仓后新保本点", f"{new_cost:.3f}", f"成本抬高 {new_cost-cost_old:.3f}" if qty_add > 0 else None, delta_color="inverse")
        r2.metric("利润安全垫", f"{safe_cushion:.2f}%")

    with col_adv:
        st.subheader("🤖 智能决策建议")
        advice_text, adv_status = generate_advice(st.session_state.df_history, cost_old, qty_add, current_p)
        
        if adv_status == "success": st.success(advice_text)
        elif adv_status == "warning": st.warning(advice_text)
        elif adv_status == "error": st.error(advice_text)
        else: st.info(advice_text)
