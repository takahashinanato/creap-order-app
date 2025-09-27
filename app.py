import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="クレープ管理アプリ", page_icon="🥞", layout="wide")

# --- Google Sheets 接続ユーティリティ ---
@st.cache_resource(show_spinner=False)
def get_gspread_client():
    creds_dict = st.secrets["GCP_SERVICE_ACCOUNT_JSON"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(credentials)

@st.cache_resource(show_spinner=False)
def open_or_create_sheet():
    gc = get_gspread_client()
    sheet_id = st.secrets["SHEET_ID"]
    sh = gc.open_by_key(sheet_id)

    def get_or_create_ws(title: str, header: list[str]):
        try:
            ws = sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=1000, cols=len(header))
            ws.append_row(header)
        return ws

    orders_ws = get_or_create_ws("orders", ["timestamp","ticket","name","menu","qty","status"]) 
    stock_ws  = get_or_create_ws("stock",  ["item","qty"]) 
    return sh, orders_ws, stock_ws

# --- データ操作 ---
def load_orders_df(ws):
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=["timestamp","ticket","name","menu","qty","status"]) 
    return df

def append_order(ws, name, menu, qty):
    df = load_orders_df(ws)
    next_ticket = (df["ticket"].max() if not df.empty else 0)
    next_ticket = int(0 if pd.isna(next_ticket) else next_ticket) + 1
    row = [datetime.now().isoformat(timespec="seconds"), next_ticket, name, menu, int(qty), "pending"]
    ws.append_row(row)
    return next_ticket

def update_order_status(ws, ticket, new_status):
    records = ws.get_all_records()
    for idx, rec in enumerate(records, start=2):  # 1行目はヘッダ
        if int(rec.get("ticket", -1)) == int(ticket):
            ws.update_cell(idx, 6, new_status)  # 6列目 = status
            return True
    return False

def load_stock_df(ws):
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame([{"item": "生地", "qty": 100}, {"item": "生クリーム", "qty": 50}])
        ws.append_row(["生地", 100])
        ws.append_row(["生クリーム", 50])
    return df

def upsert_stock(ws, item, qty):
    records = ws.get_all_records()
    for idx, rec in enumerate(records, start=2):
        if rec.get("item") == item:
            ws.update_cell(idx, 2, int(qty))
            return
    ws.append_row([item, int(qty)])

# --- UI ---
st.title("🎪 クレープ管理アプリ（ベース版）")

try:
    sh, orders_ws, stock_ws = open_or_create_sheet()
except Exception as e:
    st.error("Google Sheets 接続に失敗しました。Secrets と共有設定を確認してください。\n\n" + str(e))
    st.stop()

colA, colB = st.columns([1,1])

with colA:
    st.subheader("1) 注文入力")
    with st.form("order_form", clear_on_submit=True):
        name = st.text_input("お名前（任意）", "")
        menu = st.selectbox("メニュー", [
            "シュガー", "チョコバナナ", "いちごカスタード", "キャラメルナッツ", "ツナマヨ"
        ])
        qty = st.number_input("数量", min_value=1, max_value=10, value=1, step=1)
        submitted = st.form_submit_button("受付する")
    if submitted:
        ticket = append_order(orders_ws, name, menu, qty)
        st.success(f"受付完了！あなたの番号は **{ticket}** です。")

with colB:
    st.subheader("2) 受付状況")
    odf = load_orders_df(orders_ws)
    if odf.empty:
        st.info("まだ注文がありません。")
    else:
        latest = int(odf["ticket"].max())
        pending_df = odf[odf["status"] == "pending"]
        cooking_df = odf[odf["status"] == "cooking"]
        ready_df   = odf[odf["status"] == "ready"]

        m1, m2, m3 = st.columns(3)
        m1.metric("最新受付番号", latest)
        m2.metric("次に呼ぶ番号", int(pending_df["ticket"].min()) if not pending_df.empty else "-")
        m3.metric("現在焼いている番号", int(cooking_df["ticket"].min()) if not cooking_df.empty else "-")

        st.write("### ▶ ステータス操作（直近30件）")
        show = odf.sort_values("ticket", ascending=False).head(30).sort_values("ticket")
        st.dataframe(show, use_container_width=True, hide_index=True)

        target_ticket = st.number_input("番号を指定して操作", min_value=1, value=int(latest), step=1)
        action = st.selectbox("操作", ["pending → cooking","cooking → ready","ready → delivered"]) 
        if st.button("反映"):
            if "pending" in action:
                ok = update_order_status(orders_ws, target_ticket, "cooking")
            elif "cooking" in action:
                ok = update_order_status(orders_ws, target_ticket, "ready")
            else:
                ok = update_order_status(orders_ws, target_ticket, "delivered")
            if ok:
                st.success("更新しました。")
            else:
                st.warning("対象番号が見つかりませんでした。")

st.write("---")

st.subheader("3) 在庫")
sdf = load_stock_df(stock_ws)
st.dataframe(sdf, use_container_width=True, hide_index=True)
with st.form("stock_form"):
    item = st.text_input("品目名", "生地")
    qty = st.number_input("数量", min_value=0, value=100, step=1)
    if st.form_submit_button("在庫を登録/更新"):
        upsert_stock(stock_ws, item, qty)
        st.success("在庫を更新しました。")
