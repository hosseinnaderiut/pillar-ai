import streamlit as st
import pandas as pd
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import io

st.set_page_config(page_title="SEO AI Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color:#4472C4;'>SEO AI Pro - ابزار کلاستریگ هوشمند</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>فایل اکسل (عبارت + حجم جستجو) آپلود کن</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("", type=['xlsx', 'xls'], label_visibility="collapsed")

if uploaded_file:
    with st.spinner("در حال ادغام و تحلیل..."):

        # --------------------------
        # 1) خواندن و آماده‌سازی داده
        # --------------------------
        df = pd.read_excel(uploaded_file, usecols=[0, 1])
        df.columns = ['عبارت', 'حجم جستجو']
        df = df.dropna()
        df['حجم جستجو'] = pd.to_numeric(df['حجم جستجو'], errors='coerce')
        df = df.dropna()

        # پاک‌سازی
        def clean_text(text):
            text = str(text)
            text = re.sub(r'[\u200c\u200d\u200e\u200f]', '', text)
            text = text.replace('-', ' ').replace('_', ' ').replace('/', ' ')
            text = re.sub(r'\s+', ' ', text).strip().lower()
            return text

        df['تمیز'] = df['عبارت'].apply(clean_text)

        # ---------------------------------------
        # 2) ادغام هوشمند با استفاده از Union-Find
        # ---------------------------------------
        def is_similar(a, b):
            return SequenceMatcher(None, a, b).ratio() > 0.85

        parent = list(range(len(df)))
        rank = [0] * len(df)

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                if rank[px] < rank[py]:
                    parent[px] = py
                elif rank[px] > rank[py]:
                    parent[py] = px
                else:
                    parent[py] = px
                    rank[px] += 1

        for i in range(len(df)):
            for j in range(i + 1, len(df)):
                if is_similar(df['تمیز'].iloc[i], df['تمیز'].iloc[j]):
                    union(i, j)

        groups = defaultdict(list)
        for i in range(len(df)):
            groups[find(i)].append(i)

        new_rows = []
        merged_count = 0

        for group in groups.values():
            if len(group) > 1:
                merged_count += len(group) - 1

            total = sum(df['حجم جستجو'].iloc[i] for i in group)
            main = max(group, key=lambda i: df['حجم جستجو'].iloc[i])

            new_rows.append({
                'عبارت': df['عبارت'].iloc[main],
                'حجم جستجو': total,
                'تمیز': df['تمیز'].iloc[main]
            })

        df = pd.DataFrame(new_rows)

        # --------------------------
        # 3) Intent و H1 پیشنهادی  
        # --------------------------
        def intent_ai(text):
            text = text.lower()
            if any(k in text for k in ['خرید', 'قیمت', 'ارزان', 'تخفیف']):
                return "Transactional"
            if any(k in text for k in ['بهترین', 'مقایسه', 'بررسی']):
                return "Commercial"
            if any(k in text for k in ['طرز', 'چگونه', 'آموزش']):
                return "Informational"

            n = len(text.split())
            if n >= 5: return "Informational"
            if n <= 2: return "Navigational"
            return "Commercial"

        def h1_ai(text):
            if 'طرز' in text:
                return f"طرز تهیه {text.replace('طرز تهیه','').strip()} در خانه"
            if 'بهترین' in text:
                return f"{text} + مقایسه 1404"
            if 'خرید' in text:
                return f"خرید {text.replace('خرید','').strip()} با گارانتی"
            return text.title()[:60]

        df['Intent_AI'] = df['تمیز'].apply(intent_ai)
        df['H1 پیشنهادی'] = df['تمیز'].apply(h1_ai)

        # --------------------------
        # 4) دسته‌بندی اصلی
        # --------------------------
        df['برای دسته'] = df['تمیز'].str.replace(r'^(طرز تهیه|خرید|قیمت|بهترین)\s*', '', regex=True)

        df = df[df['برای دسته'].notna()]
        df = df[df['برای دسته'].str.strip() != ""]

        سه_کلمه = df['برای دسته'].str.split().apply(lambda x: ' '.join(x[:3]) if len(x) >= 3 else None).dropna()
        کلید_قوی = [k for k, v in Counter(سه_کلمه).items() if v >= 2]

        def assign_category(text):
            if not isinstance(text, str) or not text.strip():
                return "بدون دسته"

            for key in کلید_قوی:
                if text.startswith(key):
                    return ' '.join(key.split()[:2]).title()

            parts = text.split()
            return parts[0].title() if parts else "بدون دسته"

        df['دسته'] = df['برای دسته'].apply(assign_category)

        # --------------------------
        # 5) Page Type
        # --------------------------
        summary = df.groupby(['دسته', 'عبارت', 'Intent_AI'])['حجم جستجو'].sum().reset_index()
        total_cat = summary.groupby('دسته')['حجم جستجو'].sum().to_dict()

        def page_type(vol, cat):
            if vol == total_cat.get(cat, 0):
                return "Pillar" if vol >= 100000 else "Cluster"
            return "Sub-Cluster"

        summary['Page Type'] = summary.apply(lambda x: page_type(x['حجم جستجو'], x['دسته']), axis=1)

        # --------------------------
        # 6) خروجی اکسل با ساختار درختی
        # --------------------------
        data = []
        for (cat, intent), group in summary.groupby(['دسته', 'Intent_AI']):
            total = group['حجم جستجو'].sum()
            pt = page_type(total, cat)

            data.append([cat, total, intent, pt, ""])

            for _, r in group.iterrows():
                h1 = df[df['عبارت'] == r['عبارت']]['H1 پیشنهادی'].iloc[0]
                data.append([r['عبارت'], r['حجم جستجو'], intent, r['Page Type'], h1])

        final_table = pd.DataFrame(data, columns=['دسته / عبارت', 'حجم جستجو', 'Intent_AI', 'Page Type', 'H1 پیشنهادی'])

        # خروجی اکسل
        output = io.BytesIO()
        wb = Workbook()
        ws = wb.active

        for r_idx, row in enumerate(dataframe_to_rows(final_table, index=False, header=True), 1):
            for c_idx, value in enumerate(row, 1):
                ws.cell(r_idx, c_idx, value)

        wb.save(output)
        output.seek(0)

        st.success(f"تمام! {merged_count} عبارت ادغام شد — {len(df)} دسته ساخته شد")
        st.download_button("دانلود اکسل", output, "SEO_AI_Result.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.balloons()
