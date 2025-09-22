import streamlit as st
import os
import matplotlib.pyplot as plt

st.title("🧠 政治的バイアス診断アプリ（デモ版）")

text = st.text_area("SNS投稿を入力してください（例：憲法改正は必要だと思う）")

if st.button("診断する") and text:
    with st.spinner("診断中...（デモ版のためダミー結果を表示しています）"):
        # ダミーの診断結果（毎回ランダムに見せたい場合は randomモジュールも使える）
        reply = "傾向: 0.25, 強さ: 0.6"
        st.write("診断結果:", reply)

        # 数値抽出してグラフ化
        import re
        nums = re.findall(r"-?\d+\.\d+", reply)
        if len(nums) >= 2:
            bias = float(nums[0])
            strength = float(nums[1])

            st.success(f"傾向スコア: {bias}, 強さスコア: {strength}")

            fig, ax = plt.subplots()
            ax.scatter([bias], [strength], color='blue')
            ax.set_xlim(-1, 1)
            ax.set_ylim(0, 1)
            ax.set_xlabel("政治的傾向（保守 -1.0 ～ +1.0 リベラル）")
            ax.set_ylabel("表現の強さ（穏やか 0.0 ～ 1.0 過激）")
            st.pyplot(fig)
        else:
            st.error("数値の抽出に失敗しました。出力形式を確認してください。")
