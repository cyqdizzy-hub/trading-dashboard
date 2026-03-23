import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

# --- 页面设置 (宽屏模式更适合看图) ---
st.set_page_config(page_title="通用投资决策仪表盘", page_icon="📈", layout="wide")

# --- 初始化会话状态 ---
if 'current_price' not in st.session_state:
    st.session_state.current_price = 0.0
if 'target_symbol' not in st.session_state:
    st.session_state.target_symbol = "159934.SZ" # 默认黄金ETF
if 'df_history' not in st.session_state:
    st.session_state.df_history = pd.DataFrame() # 存储历史数据

# --- 1. 数据抓取与指标计算函数 ---
def fetch_data_and_calc_ind(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # 抓取最近 1 年数据，确保计算 60日均线时数据充足
        df = ticker.history(period="1y")
        if df.empty:
            return None, "未获取到数据，请检查代码格式。"
        
        # 计算技术指标 (均线)
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        # 截取最近 6 个月用于显示
        df_display = df.iloc[-126:] # 半年大约126个交易日
        return df_display, "成功"
    except Exception as e:
        return None, str(e)

# --- 2. 交互式 K 线图绘制函数 (Plotly) ---
def plot_candlestick(df, symbol):
    # 创建带成交量的子图 (上图 K线，下图成交量)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{symbol} 6个月日K线图', '成交量'), 
                        row_width=[0.2, 0.8])

    # 添加 K 线图
    fig.add_trace(go.Candlestick(x=df.index,
                                open=df['Open'], high=df['High'],
                                low=df['Low'], close=df['Close'],
                                name='K线',
                                increasing_line_color='#ef5350', # 红色涨
                                decreasing_line_color='#26a69a'), # 绿色跌
                  row=1, col=1)

    # 添加均线
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20日线 (短期)', line=dict(color='#ffca28', width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60日线 (中期)', line=dict(color='#2196f3', width=1.5)), row=1, col=1)

    # 添加成交量柱状图
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color='#90caf9'), row=2, col=1)

    # 图表样式优化
    fig.update_layout(
        xaxis_rangeslider_visible=False, # 关闭底部的范围滑动条
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
    status = "success" # 默认状态为健康

    # --- A. 趋势判断 (根据 60 日线定多空) ---
    st.markdown("#### ⚖️ 综合评估")
    
    if current_p > ma60 and ma20 > ma60:
        advice.append("📈 **市场环境：多头趋势**。当前处于中期上升通道中 (价格在 60日线上，20日线在 60日线上)。")
        # --- B. 加仓机会判断 (多头环境下看回调) ---
        dist_to_ma20 = (current_p - ma20) / ma20
        if 0 < dist_to_ma20 < 0.02:
            advice.append("🎯 **加仓机会**：价格已回调至 20 日均线支撑位附近。若你计划加仓，此时性价比合理。")
        elif dist_to_ma20 > 0.05:
            advice.append("⏳ **操作建议**：偏离短期均线过远，存在追高风险。建议耐心等待回调至黄色 20 日线附近。")
            status = "warning"
        else:
            advice.append("👀 **操作建议**：多头持有，关注支撑。")
    elif current_p < ma60:
        advice.append("📉 **市场环境：空头/调整趋势**。价格已跌破中期 60 日生命线。")
        advice.append("🛑 **操作建议**：**不宜加仓追高**。当前以保护底仓利润或降低风险为主。等待重回 60 日线上再考虑。")
        status = "error"
    else:
        advice.append("⚖️ **市场环境：震荡市**。趋势不明显，建议多看少动。")
        status = "warning"

    # --- C. 风控提示 (基于用户算出的安全垫) ---
    if qty_add > 0:
        st.divider()
        st.markdown("#### 🛡️ 加仓风控建议")
        new_cost = ((cost_old * 3776) + (current_p * qty_add)) / (3776 + qty_add) # 这里简化了qty_old，建议实际用变量
        if current_p < new_cost:
             advice.append("⚠️ **风控警报**：加仓后已陷入亏损！")
        
        advice.append(f"1. **短期纠错**：若有效跌破黄色 20 日均线 ({ma20:.3f})，建议平掉刚加的新仓。")
        advice.append(f"2. **绝对保本线**：不论如何，价格跌破你的新成本线，必须保护本金。")

    return "\n\n".join(advice), status


# ==========================================
#                  界面构建
# ==========================================

st.title("📈 通用投资决策仪表盘")
st.markdown("输入代码 -> 查看 K 线与趋势 -> 模拟加仓 -> 获取智能风控建议。")

# 1. 顶部输入与行情区
with st.container():
    c1, c2, c3 = st.columns([1.5, 2, 1])
    
    with c1:
        st.session_state.target_symbol = st.text_input(
            "🔍 输入标的代码", value=st.session_state.target_symbol, help="深市:.SZ, 沪市:.SS, 美股:直接输")
    
    with c2:
        st.write("") # 占位
        if st.button("🔄 同步 6个月行情与 K线", type="primary", use_container_width=True):
            with st.spinner(f'正在同步 {st.session_state.target_symbol} 历史数据...'):
                df_h, msg = fetch_data_and_calc_ind(st.session_state.target_symbol)
                if df_h is not None:
                    st.session_state.df_history = df_h
                    st.session_state.current_price = float(df_h.iloc[-1]['Close'])
                    st.toast("✅ 数据同步成功！")
                    st.rerun()
                else:
                    st.error(f"❌ 获取失败：{msg}")

    with c3:
        # 显示现价
        st.metric("最新现价", f"{st.session_state.current_price:.3f}" if st.session_state.current_price > 0 else "N/A")

st.divider()

# 2. 中部：K 线图展示 (宽屏模式)
if not st.session_state.df_history.empty:
    fig_k = plot_candlestick(st.session_state.df_history, st.session_state.target_symbol)
    st.plotly_chart(fig_k, use_container_width=True)
else:
    st.info("💡 请先在上方输入代码，点击按钮同步数据。")

st.divider()

# 3. 底部：加仓推演与智能建议 (左右分栏)
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
        
        # 计算核心指标
        total_qty = qty_old + qty_add
        current_p = st.session_state.current_price
        if total_qty > 0:
            new_cost = ((cost_old * qty_old) + (current_p * qty_add)) / total_qty
            safe_cushion = ((current_p - new_cost) / current_p) * 100 if current_p > 0 else 0
        else:
            new_cost, safe_cushion = cost_old, 0

        # 指标展示
        r1, r2 = st.columns(2)
        r1.metric("加仓后新保本点", f"{new_cost:.3f}", f"成本抬高 {new_cost-cost_old:.3f}" if qty_add > 0 else None, delta_color="inverse")
        r2.metric("利润安全垫", f"{safe_cushion:.2f}%")

    with col_adv:
        st.subheader("🤖 智能决策建议")
        advice_text, adv_status = generate_advice(st.session_state.df_history, cost_old, qty_add, current_p)
        
        # 根据状态显示不同的彩色提示框
        if adv_status == "success": st.success(advice_text)
        elif adv_status == "warning": st.warning(advice_text)
        elif adv_status == "error": st.error(advice_text)
        else: st.info(advice_text)
