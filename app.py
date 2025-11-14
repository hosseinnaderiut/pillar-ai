import streamlit as st
import pandas as pd

st.set_page_config(page_title="دسته‌بندی کلمات", layout="wide")

st.title("دسته‌بندی خودکار کلمات (AI Friendly)")

# --------------------------
# تابع امن برای تخصیص دسته
# --------------------------
def تخصیص_دسته(متن):
    if pd.isna(متن) or not isinstance(متن, str):
        return ""
    متن = متن.strip()
    if متن == "":
        return ""
    بخش‌ها = متن.split()
    if len(بخش‌ها) == 0:
        return ""
    return بخش‌ها[0].title()

# --------------------------
# بارگذاری فایل
# --------------------------
uploaded_file = st.file_uploader("فایل اکسل را آپلود کنید", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if "برای_دسته" not in df.columns:
        st.error("❌ ستون «برای_دسته» در فایل شما وجود ندارد.")
        st.stop()

    # اعمال تابع جدید
    df["دسته"] = df["برای_دسته"].apply(تخصیص_دسته)

    st.success("✅ دسته‌بندی انجام شد!")

    # نمایش دیتا
    st.dataframe(df, use_container_width=True)

    # دانلود خروجی
    @st.cache_data
    def convert_df_to_excel(df):
        from io import BytesIO
        output = BytesIO()
        df.to_excel(output, index=False, encoding="utf-8")
        processed_data = output.getvalue()
        return processed_data

    excel_data = convert_df_to_excel(df)

    st.download_button(
        label="📥 دانلود فایل خروجی",
        data=excel_data,
        file_name="output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
