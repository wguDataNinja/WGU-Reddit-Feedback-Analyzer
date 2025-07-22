# app.py

import streamlit as st
import pandas as pd

@st.cache_data
def load_data():
    df_codes = pd.read_csv("/WGU_catalog/all_course_codes.csv")
    df_matrix = pd.read_csv("WGU_catalog/docs/archive/course_year_presence_matrix.csv")
    return df_codes, df_matrix

def search_courses(df_codes, query):
    q = query.strip().lower()
    if not q:
        return pd.DataFrame(columns=df_codes.columns)
    mask_code = df_codes['CourseCode'].str.lower().str.contains(q)
    mask_name = df_codes['CourseName'].str.lower().str.contains(q)
    mask_ccn = df_codes['CCN'].str.lower().str.contains(q)  # NEW: search in CCN
    return df_codes[mask_code | mask_name | mask_ccn]

def display_course_details(code, df_codes, df_matrix):
    course = df_codes[df_codes['CourseCode'] == code].iloc[0]
    matrix_row = df_matrix[df_matrix['CourseCode'] == code].iloc[0]
    st.header(course['CourseName'])
    st.subheader(f"Course Code: {course['CourseCode']}")
    st.write(f"CCN: {course['CCN']}")
    st.subheader("Presence by Year")
    years = list(range(2017, 2026))
    cols = st.columns(len(years))
    for i, year in enumerate(years):
        val = matrix_row[str(year)]
        with cols[i]:
            st.write(year)
            st.write("✅" if val == 1 else "❌")

def truncate_label(label, max_len=30):
    return label if len(label) <= max_len else label[:max_len - 3] + "..."

def main():
    st.title("WGU Course Presence Explorer")

    df_codes, df_matrix = load_data()

    search_query = st.text_input("Search courses by code or name")

    if 'last_query' not in st.session_state:
        st.session_state['last_query'] = ""
    if 'selected_course' not in st.session_state:
        st.session_state['selected_course'] = None

    if search_query != st.session_state['last_query']:
        st.session_state['selected_course'] = None
        st.session_state['last_query'] = search_query

    matches = search_courses(df_codes, search_query)

    selected = st.session_state['selected_course']
    if selected is None and len(matches) == 1:
        selected = matches.iloc[0]['CourseCode']

    if selected is None:
        if len(matches) > 1:
            with st.container():
                st.subheader("Matching courses")
                max_cols = 4
                rows = [matches.iloc[i:i + max_cols] for i in range(0, len(matches), max_cols)]
                for row in rows:
                    cols = st.columns(len(row))
                    for col, (_, course) in zip(cols, row.iterrows()):
                        with col:
                            raw_label = f"{course['CourseCode']} – {course['CourseName']}"
                            label = truncate_label(raw_label)
                            # Padding to ensure equal height
                            padded_label = f"{label}\n\n"  # forces button height consistency
                            if st.button(padded_label, key=f"btn_{course['CourseCode']}"):
                                st.session_state['selected_course'] = course['CourseCode']
                                selected = course['CourseCode']
        elif search_query:
            st.info("No courses found. Try a different query.")
    else:
        display_course_details(selected, df_codes, df_matrix)

if __name__ == "__main__":
    main()