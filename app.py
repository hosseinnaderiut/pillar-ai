import streamlit as st
import pandas as pd
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.utils.dataframe import dataframe_to_rows
import io

st.set_page_config(page_title="SEO AI Pro", layout="wide")
st.markdown("<h1 style='text-align: center; color:#4472C4;'>SEO AI Pro - ابزار کلاستریگ هوشمند</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>فایل اکسل (عبارت + حجم جستجو) آپلود کن</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("", type=['xlsx', 'xls'], label_visibility="collapsed")

if uploaded_file:
    with st.spinner("در حال ادغام و تحلیل..."):
        df = pd.read_excel(uploaded_file, usecols=[0, 1])
        df.columns = ['عبارت', 'حجم جستجو']
        df = df.dropna()
        df['حجم جستجو'] = pd.to_numeric(df['حجم جستجو'], errors='coerce')
        df = df.dropna()

        # تمیز کردن
        def تمیز(متن):
            متن = str(متن)
            متن = re.sub(r'[\u200c\u200d\u200e\u200f]', '', متن)
            متن = متن.replace('-', ' ').replace('_', ' ').replace('/', ' ')
            متن = re.sub(r'\s+', ' ', متن).strip().lower()
            return متن
        df['تمیز'] = df['عبارت'].apply(تمیز)

        # ادغام هوشمند
        def مشابه(س1, س2):
            return SequenceMatcher(None, س1, س2).ratio() > 0.85

        parent = list(range(len(df)))
        rank = [0] * len(df)
        def find(x): 
            if parent[x] != x: parent[x] = find(parent[x])
            return parent[x]
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                if rank[px] < rank[py]: parent[px] = py
                elif rank[px] > rank[py]: parent[py] = px
                else: parent[py] = px; rank[px] += 1

        for i in range(len(df)):
            for j in range(i+1, len(df)):
                if مشابه(df['تمیز'].iloc[i], df['تمیز'].iloc[j]):
                    union(i, j)

        groups = defaultdict(list)
        for i in range(len(df)): groups[find(i)].append(i)

        new_rows = []
        ادغام_شده = 0
        for group in groups.values():
            if len(group) > 1: ادغام_شده += len(group) - 1
            total = sum(df['حجم جستجو'].iloc[k] for k in group)
            main = max(group, key=lambda k: df['حجم جستجو'].iloc[k])
            new_rows.append({'عبارت': df['عبارت'].iloc[main], 'حجم جستجو': total, 'تمیز': df['تمیز'].iloc[main]})
        df = pd.DataFrame(new_rows)

        # Intent + H1
        def intent_ai(متن):
            متن = متن.lower()
            if any(k in متن for k in ['خرید','قیمت','ارزان','تخفیف']): return "Transactional"
            if any(k in متن for k in ['بهترین','مقایسه','بررسی']): return "Commercial"
            if any(k in متن for k in ['طرز','چگونه','آموزش']): return "Informational"
            n = len(متن.split())
            return "Informational" if n >= 5 else ("Navigational" if n <= 2 else "Commercial")

        def h1_ai(متن):
            if 'طرز' in متن: return f"طرز تهیه {متن.replace('طرز تهیه','').strip()} در خانه"
            if 'بهترین' in متن: return f"{متن} + مقایسه 1404"
            if 'خرید' in متن: return f"خرید {متن.replace('خرید','').strip()} با گارانتی"
            return متن.title()[:60]

        df['Intent_AI'] = df['تمیز'].apply(intent_ai)
        df['H1_پیشنهادی'] = df['تمیز'].apply(h1_ai)

        # دسته‌بندی
        df['برای_دسته'] = df['تمیز'].str.replace(r'^(طرز تهیه|خرید|قیمت|بهترین)\s*','', regex=True)
        سه_کلمه = df['برای_دسته'].str.split().apply(lambda x: ' '.join(x[:3]) if len(x)>=3 else None).dropna()
        کلید_قوی = [k for k,v in Counter(سه_کلمه).items() if v>=2]

        def تخصیص_دسته(متن):
            for ک in کلید_قوی:
                if متن.startswith(ک): return ' '.join(ک.split()[:2]).title()
            return متن.split()[0].title()
        df['دسته'] = df['برای_دسته'].apply(تخصیص_دسته)

        # Page Type
        خلاصه = df.groupby(['دسته','عبارت','Intent_AI'])['حجم جستجو'].sum().reset_index()
        جمع_دسته = خلاصه.groupby('دسته')['حجم جستجو'].sum().to_dict()
        def page_type(حجم, دسته):
            if حجم == جمع_دسته.get(دسته,0):
                return "Pillar" if حجم >= 100000 else "Cluster"
            return "Sub-Cluster"
        خلاصه['Page Type'] = خلاصه.apply(lambda x: page_type(x['حجم جستجو'], x['دسته']), axis=1)

        # خروجی اکسل
        داده = []
        for (دسته, intent), گروه in خلاصه.groupby(['دسته','Intent_AI']):
            جمع = گروه['حجم جستجو'].sum()
            pt = page_type(جمع, دسته)
            داده.append([دسته, جمع, intent, pt, ""])
            for _, r in گروه.iterrows():
                h1 = df[df['عبارت']==r['عبارت']]['H1_پیشنهادی'].iloc[0]
                داده.append([r['عبارت'], r['حجم جستجو'], intent, r['Page Type'], h1])

        جدول = pd.DataFrame(داده, columns=['دسته / عبارت','حجم جستجو','Intent_AI','Page Type','H1 پیشنهادی'])

        output = io.BytesIO()
        wb = Workbook()
        ws = wb.active
        for r_idx, row in enumerate(dataframe_to_rows(جدول, index=False, header=True), 1):
            for c_idx, value in enumerate(row, 1):
                ws.cell(r_idx, c_idx, value)
        wb.save(output)
        output.seek(0)

        st.success(f"تمام! {ادغام_شده} عبارت ادغام شد — {len(df)} دسته")
        st.download_button("دانلود اکسل", output, "نتایج_SEO_AI.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.balloons()
